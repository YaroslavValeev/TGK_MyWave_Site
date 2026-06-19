#!/usr/bin/env python3
"""Create Social_Applications tab on Admin sheet (header row only).

GM-approved remediation B — Admin spreadsheet only.

Dry-run (default):
  PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python scripts/prod_create_social_applications_tab.py

Apply (creates tab + writes row 1 headers if tab missing):
  SOCIAL_TAB_CREATE_APPLY=1 PROD_ROOT=/var/www/mywave \\
    /var/www/mywave/venv/bin/python scripts/prod_create_social_applications_tab.py

Does not: write application rows, touch Parser sheet, booking/client tabs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROD_ROOT = Path(os.environ.get("PROD_ROOT", "/var/www/mywave"))
APPLY = os.environ.get("SOCIAL_TAB_CREATE_APPLY", "").strip() in {"1", "true", "yes", "YES"}


def main() -> int:
    sys.path.insert(0, str(PROD_ROOT))
    os.chdir(PROD_ROOT)

    from app import create_app
    from app.services.social_schema import (
        SOCIAL_APPLICATIONS_HEADERS,
        SOCIAL_APPLICATIONS_SHEET,
        validate_sheet_headers,
    )

    app = create_app("production")
    with app.app_context():
        sid = (
            (app.config.get("SOCIAL_SPREADSHEET_ID") or "").strip()
            or (app.config.get("SPREADSHEET_ID") or "").strip()
        )
        sheet_name = (
            app.config.get("SOCIAL_APPLICATIONS_SHEET_NAME") or SOCIAL_APPLICATIONS_SHEET
        ).strip()

        if not sid:
            print("FAIL: no SOCIAL_SPREADSHEET_ID / SPREADSHEET_ID in config")
            return 1

        print("=== Social_Applications tab setup ===")
        print(f"mode={'APPLY' if APPLY else 'DRY_RUN'}")
        print(f"spreadsheet_tail ...{sid[-8:]}")
        print(f"tab_name={sheet_name}")
        print(f"headers_count={len(SOCIAL_APPLICATIONS_HEADERS)}")
        print("headers_source=app/services/social_schema.py SOCIAL_APPLICATIONS_HEADERS")
        print("header_row_csv:")
        print(",".join(SOCIAL_APPLICATIONS_HEADERS))

        from app.services.google import get_google_services

        _, sheets, _ = get_google_services()
        meta = sheets.spreadsheets().get(spreadsheetId=sid).execute()
        titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

        if sheet_name in titles:
            print(f"tab_exists=YES")
            rng = f"{sheet_name}!1:1"
            row1 = (
                sheets.spreadsheets()
                .values()
                .get(spreadsheetId=sid, range=rng)
                .execute()
                .get("values", [[]])
            )
            headers = row1[0] if row1 else []
            ok, missing = validate_sheet_headers(sheet_name, headers)
            print(f"headers_valid={'YES' if ok else 'NO'}")
            if not ok:
                print("missing_headers:", ", ".join(missing))
                print("ACTION: fix row 1 manually to match header_row_csv (no data rows)")
            return 0 if ok else 2

        print("tab_exists=NO")
        if not APPLY:
            print("STOP: dry-run only. To create tab + headers:")
            print("  SOCIAL_TAB_CREATE_APPLY=1 PROD_ROOT=/var/www/mywave \\")
            print("    /var/www/mywave/venv/bin/python scripts/prod_create_social_applications_tab.py")
            return 0

        sheets.spreadsheets().batchUpdate(
            spreadsheetId=sid,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        ).execute()
        print("tab_created=YES")

        sheets.spreadsheets().values().update(
            spreadsheetId=sid,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": [list(SOCIAL_APPLICATIONS_HEADERS)]},
        ).execute()
        print("header_row_written=YES")
        print("data_rows=0 (by design)")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
