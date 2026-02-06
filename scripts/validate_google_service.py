#!/usr/bin/env python3
"""
scripts/validate_google_service.py

Простой инструмент для проверки service_account.json и при желании проверки доступа к Google Sheets.

Usage:
  python scripts/validate_google_service.py --key path/to/service_account.json [--spreadsheet SPREADSHEET_ID]

Если проверка успешна, скрипт вернёт exit code 0 и напишет подсказки; иначе вернёт код != 0.
"""
import argparse
import json
import os
import sys


def main():
    p = argparse.ArgumentParser(
        description="Validate Google service account JSON and optionally test Sheets access"
    )
    p.add_argument("--key", "-k", required=True, help="Path to service_account.json")
    p.add_argument(
        "--spreadsheet", "-s", required=False, help="Spreadsheet ID to test access"
    )
    args = p.parse_args()

    key_path = os.path.expanduser(args.key)
    if not os.path.exists(key_path):
        print(f"ERROR: key file not found: {key_path}", file=sys.stderr)
        sys.exit(2)

    try:
        with open(key_path, "r", encoding="utf-8") as f:
            info = json.load(f)
    except Exception as e:
        print(f"ERROR: failed to parse JSON: {e}", file=sys.stderr)
        sys.exit(3)

    # Basic checks
    for req in ("type", "client_email", "private_key"):
        if req not in info:
            print(
                f'ERROR: required field "{req}" missing in service account JSON',
                file=sys.stderr,
            )
            sys.exit(4)

    print("Service account JSON looks OK (contains type, client_email, private_key).")

    if args.spreadsheet:
        # Try to build a sheets client
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except Exception as e:
            print(
                "ERROR: google libraries not available (google-auth/google-api-python-client).",
                file=sys.stderr,
            )
            print(
                "Install with: pip install google-auth google-api-python-client",
                file=sys.stderr,
            )
            sys.exit(5)

        scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
        try:
            creds = service_account.Credentials.from_service_account_file(
                key_path, scopes=scopes
            )
            service = build("sheets", "v4", credentials=creds, cache_discovery=False)
            # attempt to read metadata
            sheet = service.spreadsheets().get(spreadsheetId=args.spreadsheet).execute()
            title = sheet.get("properties", {}).get("title")
            print(f"Successfully accessed spreadsheet: {title or args.spreadsheet}")
            sys.exit(0)
        except Exception as e:
            print(f"ERROR: failed to access spreadsheet: {e}", file=sys.stderr)
            if (
                "invalid_grant" in str(e)
                or "invalid_signature" in str(e)
                or "invalid" in str(e).lower()
            ):
                print(
                    "Hint: invalid_grant / invalid signature typically means the private_key or timezone is wrong, or the service account json is malformed.",
                    file=sys.stderr,
                )
            sys.exit(6)

    print("No spreadsheet test requested — basic JSON validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
