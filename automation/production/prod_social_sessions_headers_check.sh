#!/usr/bin/env bash
# Read-only probe: Social_Sessions + Social_Audit_Log tabs and PR56 headers.
set -euo pipefail

PROD_ROOT="${PROD_ROOT:-/var/www/mywave}"
export PROD_ROOT

echo "=== prod_social_sessions_headers_check (read-only) ==="

"${PROD_ROOT}/venv/bin/python" - <<'PY'
import os
import sys
from pathlib import Path

PROD_ROOT = Path(os.environ.get("PROD_ROOT", "/var/www/mywave"))
sys.path.insert(0, str(PROD_ROOT))
os.chdir(PROD_ROOT)

from app.services.social_schema import (
    SOCIAL_AUDIT_LOG_HEADERS,
    SOCIAL_AUDIT_LOG_SHEET,
    SOCIAL_SESSIONS_HEADERS,
    SOCIAL_SESSIONS_SHEET,
    validate_sheet_headers,
)

import importlib.util

_spec = importlib.util.spec_from_file_location(
    "_prod_env",
    str(PROD_ROOT / "automation" / "production" / "_prod_env.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
_mod.load_prod_dotenv(str(PROD_ROOT))

from app import create_app

app = create_app("production")
with app.app_context():
    from app.services.google import get_google_services
    from app.services.social_store import resolve_social_spreadsheet_id

    sid = resolve_social_spreadsheet_id()
    if not sid:
        raise SystemExit("FAIL: no SPREADSHEET_ID / SOCIAL_SPREADSHEET_ID")
    print("spreadsheet_tail", sid[-8:])

    _, sheets, _ = get_google_services()
    meta = sheets.spreadsheets().get(spreadsheetId=sid).execute()
    titles = {s["properties"]["title"] for s in meta.get("sheets", [])}

    for sheet_name, contract in (
        (SOCIAL_SESSIONS_SHEET, SOCIAL_SESSIONS_HEADERS),
        (SOCIAL_AUDIT_LOG_SHEET, SOCIAL_AUDIT_LOG_HEADERS),
    ):
        present = sheet_name in titles
        print(f"tab_{sheet_name}", "YES" if present else "NO")
        if not present:
            print(f"ACTION_REQUIRED: create tab '{sheet_name}' with headers:")
            print(",".join(contract))
            continue
        rng = f"'{sheet_name}'!1:1"
        row = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=sid, range=rng)
            .execute()
            .get("values", [[]])
        )
        headers = row[0] if row else []
        ok, missing = validate_sheet_headers(sheet_name, headers)
        print(f"headers_{sheet_name}_ok", ok)
        if missing:
            print(f"headers_{sheet_name}_missing", ",".join(missing))
            print(f"ACTION_REQUIRED: update row 1 to:")
            print(",".join(contract))

print("HEADERS_CHECK=COMPLETE")
PY
