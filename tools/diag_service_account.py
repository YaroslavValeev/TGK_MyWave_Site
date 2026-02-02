import os
import json
import hashlib
import traceback
import sys
from pathlib import Path

# Ensure repo root is on sys.path so 'app' package can be imported when run as a script
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from app.config import GOOGLE_SERVICE_ACCOUNT_FILE

out = []
out.append(f"GOOGLE_SERVICE_ACCOUNT_FILE={GOOGLE_SERVICE_ACCOUNT_FILE}")
exists = os.path.isfile(GOOGLE_SERVICE_ACCOUNT_FILE)
out.append(f"exists={exists}")
if exists:
    try:
        size = os.path.getsize(GOOGLE_SERVICE_ACCOUNT_FILE)
        out.append(f"file_size={size}")
        with open(GOOGLE_SERVICE_ACCOUNT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        pk = data.get("private_key", "")
        out.append(f"private_key_present={bool(pk)}")
        sha = hashlib.sha256(pk.encode("utf-8")).hexdigest()
        out.append(f"private_key_sha256={sha}")
        # whole file hash
        with open(GOOGLE_SERVICE_ACCOUNT_FILE, "rb") as f:
            file_sha = hashlib.sha256(f.read()).hexdigest()
        out.append(f"file_sha256={file_sha}")

        # Try to refresh credentials token
        try:
            from google.oauth2 import service_account
            from google.auth.transport.requests import Request

            scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]
            creds = service_account.Credentials.from_service_account_info(
                data, scopes=scopes
            )
            req = Request()
            creds.refresh(req)
            out.append(
                f"refresh_ok=True token_len={len(creds.token) if creds.token else 0}"
            )
        except Exception as e:
            out.append("refresh_ok=False")
            out.append(f"refresh_exception={type(e).__name__}: {str(e)}")
            out.append("traceback:")
            out.extend(traceback.format_exc().splitlines())
        # Try to load private key with cryptography to validate format
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.backends import default_backend

            if pk:
                key = serialization.load_pem_private_key(
                    pk.encode("utf-8"), password=None, backend=default_backend()
                )
                # If key loaded, report basic properties
                try:
                    ksize = getattr(key, "key_size", None)
                    out.append(f"private_key_loaded=True key_size={ksize}")
                except Exception:
                    out.append("private_key_loaded=True key_size=unknown")
            else:
                out.append("private_key_loaded=False (no key)")
        except Exception as e:
            out.append("private_key_loaded=False")
            out.append(f"private_key_load_error={type(e).__name__}: {e}")
            out.append("private_key_traceback:")
            out.extend(traceback.format_exc().splitlines())
    except Exception as e:
        out.append(f"load_error={type(e).__name__}: {e}")
        out.append("traceback:")
        out.extend(traceback.format_exc().splitlines())
else:
    out.append("file missing - check GOOGLE_SERVICE_ACCOUNT_FILE or config")

import time

out.append(f"system_time={time.time()}")
out.append(f"localtime={time.asctime(time.localtime())}")

print("\n".join(out))
# Also save to tmp file for inspection
with open(
    os.path.join(os.path.dirname(__file__), "..", "tmp_service_account_diag.txt"),
    "w",
    encoding="utf-8",
) as f:
    f.write("\n".join(out))
