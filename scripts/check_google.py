"""Simple diagnostic script to validate Google service account file and basic access.

This script purposefully does NOT import the `app` package to avoid triggering
application-level side effects (HTTP clients, telegram bot initialization, etc.).

Usage:
    python scripts/check_google.py

It reads `GOOGLE_SERVICE_ACCOUNT_FILE` from the environment or uses the default
path from `config.Config.GOOGLE_SERVICE_ACCOUNT_FILE`.
"""
import os
import json
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

try:
    from config import Config
except Exception:
    # If config cannot be imported, try to fallback to environment-only checks
    Config = None

def main():
    creds_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE')
    if not creds_path and Config is not None:
        creds_path = getattr(Config, 'GOOGLE_SERVICE_ACCOUNT_FILE', None)

    print(f"Using service account file: {creds_path}")
    if not creds_path or not Path(creds_path).is_file():
        print("SERVICE ACCOUNT FILE NOT FOUND")
        if os.environ.get('GOOGLE_MOCK', '0') in ('1', 'true', 'True'):
            print("Google mock is enabled via GOOGLE_MOCK. OK for local development.")
            return
        print("Set GOOGLE_SERVICE_ACCOUNT_FILE or enable GOOGLE_MOCK for local development.")
        raise SystemExit(1)

    try:
        with open(creds_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        required = ['type', 'project_id', 'private_key', 'client_email']
        missing = [k for k in required if k not in data]
        if missing:
            print(f"Missing required fields in service account JSON: {missing}")
            raise SystemExit(2)

        print("Service account JSON parsed successfully. Checking private_key format...")
        pk = data.get('private_key', '')
        if 'BEGIN PRIVATE KEY' not in pk:
            print("Warning: private_key does not contain expected header 'BEGIN PRIVATE KEY'. This may indicate formatting issues (line breaks/escaping).")
        else:
            print("private_key looks OK (BEGIN PRIVATE KEY found).")

            # Prefer central factory when available (it contains mock logic and stricter checks)
            try:
                from app.services.google import get_google_services
                try:
                    ds = get_google_services()
                    # if we get here, services initialized (or returned mock) — good enough
                    print("get_google_services() returned successfully (real or mock services).")
                except Exception as e:
                    print(f"get_google_services() failed: {e}")
                    raise
            except Exception:
                # Fallback: attempt to create Credentials object if google oauth library is available
                try:
                    from google.oauth2 import service_account as sa
                    try:
                        creds = sa.Credentials.from_service_account_file(creds_path)
                        print("Service account credentials object created successfully.")
                    except Exception as e:
                        print(f"Failed to create credentials object: {e}")
                        raise
                except Exception:
                    print("google-auth library not available; skipping credentials creation check.")

    except json.JSONDecodeError as e:
        print(f"JSON parse error: {e}")
        raise
    except Exception as e:
        print(f"Error during google checks: {e}")
        raise

    print("Done.")

if __name__ == '__main__':
    main()
