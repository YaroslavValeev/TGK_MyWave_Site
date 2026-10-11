#!/usr/bin/env python3
"""Create Social_Sessions + Social_Audit_Log tabs (header row only, PR56).

Admin spreadsheet only — same pattern as prod_create_social_applications_tab.py.

Dry-run (default):
  PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python scripts/prod_create_social_pr56_tabs.py

Apply (creates missing tabs + writes row 1 headers):
  SOCIAL_TAB_CREATE_APPLY=1 PROD_ROOT=/var/www/mywave \\
    /var/www/mywave/venv/bin/python scripts/prod_create_social_pr56_tabs.py

Does not: write session/application rows, touch booking/parser tabs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

PROD_ROOT = Path(os.environ.get("PROD_ROOT", "/var/www/mywave"))
APPLY = os.environ.get("SOCIAL_TAB_CREATE_APPLY", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _ensure_tab(
    *,
    sheets,
    sid: str,
    sheet_name: str,
    headers: Sequence[str],
    titles: List[str],
    validate_sheet_headers,
) -> int:
    """Returns 0 ok, 2 headers mismatch on existing tab."""
    print(f"--- {sheet_name} ---")
    print(f"headers_count={len(headers)}")
    print("header_row_csv:")
    print(",".join(headers))

    if sheet_name in titles:
        print("tab_exists=YES")
        rng = f"'{sheet_name}'!1:1"
        row1 = (
            sheets.spreadsheets()
            .values()
            .get(spreadsheetId=sid, range=rng)
            .execute()
            .get("values", [[]])
        )
        present = row1[0] if row1 else []
        ok, missing = validate_sheet_headers(sheet_name, present)
        print(f"headers_valid={'YES' if ok else 'NO'}")
        if not ok:
            print("missing_headers:", ", ".join(missing))
            if APPLY:
                sheets.spreadsheets().values().update(
                    spreadsheetId=sid,
                    range=f"'{sheet_name}'!A1",
                    valueInputOption="RAW",
                    body={"values": [list(headers)]},
                ).execute()
                print("header_row_repaired=YES")
                return 0
            print("ACTION: fix row 1 manually or re-run with SOCIAL_TAB_CREATE_APPLY=1")
            return 2
        return 0

    print("tab_exists=NO")
    if not APPLY:
        print("STOP: dry-run — tab not created")
        return 0

    sheets.spreadsheets().batchUpdate(
        spreadsheetId=sid,
        body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
    ).execute()
    print("tab_created=YES")

    sheets.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"'{sheet_name}'!A1",
        valueInputOption="RAW",
        body={"values": [list(headers)]},
    ).execute()
    print("header_row_written=YES")
    print("data_rows=0 (by design)")
    return 0


def main() -> int:
    sys.path.insert(0, str(PROD_ROOT))
    os.chdir(PROD_ROOT)

    from app import create_app
    from app.services.social_schema import (
        SOCIAL_AUDIT_LOG_HEADERS,
        SOCIAL_AUDIT_LOG_SHEET,
        SOCIAL_SESSIONS_HEADERS,
        SOCIAL_SESSIONS_SHEET,
        validate_sheet_headers,
    )
    from app.services.social_store import resolve_social_spreadsheet_id

    app = create_app("production")
    with app.app_context():
        sid = resolve_social_spreadsheet_id()
        if not sid:
            print("FAIL: no SOCIAL_SPREADSHEET_ID / SPREADSHEET_ID in config")
            return 1

        print("=== Social PR56 tabs setup ===")
        print(f"mode={'APPLY' if APPLY else 'DRY_RUN'}")
        print(f"spreadsheet_tail ...{sid[-8:]}")
        print("headers_source=app/services/social_schema.py")

        from app.services.google import get_google_services

        _, sheets, _ = get_google_services()
        meta = sheets.spreadsheets().get(spreadsheetId=sid).execute()
        titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

        rc = 0
        for sheet_name, headers in (
            (SOCIAL_SESSIONS_SHEET, SOCIAL_SESSIONS_HEADERS),
            (SOCIAL_AUDIT_LOG_SHEET, SOCIAL_AUDIT_LOG_HEADERS),
        ):
            code = _ensure_tab(
                sheets=sheets,
                sid=sid,
                sheet_name=sheet_name,
                headers=headers,
                titles=titles,
                validate_sheet_headers=validate_sheet_headers,
            )
            if code != 0:
                rc = code
            if sheet_name not in titles and APPLY:
                titles.append(sheet_name)

        if not APPLY and rc == 0:
            missing = [n for n, _ in (
                (SOCIAL_SESSIONS_SHEET, SOCIAL_SESSIONS_HEADERS),
                (SOCIAL_AUDIT_LOG_SHEET, SOCIAL_AUDIT_LOG_HEADERS),
            ) if n not in titles]
            if missing:
                print("")
                print("To create missing tabs + headers:")
                print("  SOCIAL_TAB_CREATE_APPLY=1 PROD_ROOT=/var/www/mywave \\")
                print("    /var/www/mywave/venv/bin/python scripts/prod_create_social_pr56_tabs.py")

        print(f"RESULT={'PASS' if rc == 0 else 'NEEDS_ACTION'}")
        return rc


if __name__ == "__main__":
    raise SystemExit(main())
