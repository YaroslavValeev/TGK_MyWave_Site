#!/usr/bin/env python3
"""Verify/create Online Coaching sheet headers on Admin SPREADSHEET_ID.

Idempotent rules:
- Never overwrite data rows (only row 1 headers).
- If tab exists: report missing headers; with APPLY append missing columns to row 1.
- Media_Files: if tab already exists with any headers, skip creation (reuse).
- Online_Reviews: not auto-created in MVP.

Dry-run (default):
  python scripts/ensure_online_coaching_sheets.py

Apply (create missing tabs + append missing header cells):
  ONLINE_COACHING_SHEETS_APPLY=1 python scripts/ensure_online_coaching_sheets.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROD_ROOT = Path(os.environ.get("PROD_ROOT", Path(__file__).resolve().parents[1]))
APPLY = os.environ.get("ONLINE_COACHING_SHEETS_APPLY", "").strip().lower() in {"1", "true", "yes"}


def _norm(value: object) -> str:
    return str(value or "").strip().lower()


def _append_missing_headers(
    sheets,
    sid: str,
    sheet_name: str,
    present: list,
    expected: tuple,
) -> list[str]:
    """Append missing header names to row 1 without touching data rows."""
    present_norm = {_norm(h) for h in present if _norm(h)}
    missing = [h for h in expected if _norm(h) not in present_norm]
    if not missing or not APPLY:
        return missing

    new_row = list(present) + missing
    sheets.spreadsheets().values().update(
        spreadsheetId=sid,
        range=f"{sheet_name}!1:1",
        valueInputOption="RAW",
        body={"values": [new_row]},
    ).execute()
    print(f"headers_appended={','.join(missing)}")
    return []


def main() -> int:
    sys.path.insert(0, str(PROD_ROOT))
    os.chdir(PROD_ROOT)

    from app import create_app
    from app.services.online_coaching_schema import (
        MEDIA_FILES_SHEET,
        MVP_SHEET_CONTRACTS,
        validate_sheet_headers,
    )

    app = create_app(os.environ.get("FLASK_CONFIG", "development"))
    with app.app_context():
        sid = (app.config.get("SPREADSHEET_ID") or "").strip()
        if not sid:
            print("FAIL: SPREADSHEET_ID is empty")
            return 1

        print("=== Online Coaching sheets check ===")
        print(f"mode={'APPLY' if APPLY else 'DRY_RUN'}")
        print(f"spreadsheet_tail ...{sid[-8:]}")
        print(f"mvp_tabs={len(MVP_SHEET_CONTRACTS)}")

        from app.services.google import get_google_services

        _, sheets, _ = get_google_services()
        meta = sheets.spreadsheets().get(spreadsheetId=sid).execute()
        titles = [s["properties"]["title"] for s in meta.get("sheets", [])]

        exit_code = 0
        created = skipped = updated = 0

        for sheet_name, headers in MVP_SHEET_CONTRACTS.items():
            print(f"\n-- {sheet_name} --")
            if sheet_name in titles:
                row1 = (
                    sheets.spreadsheets()
                    .values()
                    .get(spreadsheetId=sid, range=f"{sheet_name}!1:1")
                    .execute()
                    .get("values", [[]])
                )
                present = row1[0] if row1 else []
                ok, missing = validate_sheet_headers(sheet_name, present)
                print(f"tab_exists=YES headers_valid={'YES' if ok else 'NO'}")
                if sheet_name == MEDIA_FILES_SHEET and present:
                    print("media_files_action=REUSE existing tab (no overwrite)")
                    skipped += 1
                    if not ok:
                        print("missing_headers:", ", ".join(missing))
                        still_missing = _append_missing_headers(sheets, sid, sheet_name, present, headers)
                        if still_missing:
                            exit_code = 2
                        elif missing and APPLY:
                            updated += 1
                    continue
                if not ok:
                    print("missing_headers:", ", ".join(missing))
                    still_missing = _append_missing_headers(sheets, sid, sheet_name, present, headers)
                    if still_missing:
                        exit_code = max(exit_code, 2)
                    elif missing and APPLY:
                        updated += 1
                        print("headers_action=APPENDED to row 1")
                    elif missing:
                        exit_code = max(exit_code, 2)
                else:
                    skipped += 1
                continue

            print("tab_exists=NO")
            if not APPLY:
                print("ACTION: set ONLINE_COACHING_SHEETS_APPLY=1 to create tab")
                exit_code = max(exit_code, 1)
                continue

            sheets.spreadsheets().batchUpdate(
                spreadsheetId=sid,
                body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
            ).execute()
            sheets.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"{sheet_name}!A1",
                valueInputOption="RAW",
                body={"values": [list(headers)]},
            ).execute()
            print("tab_created=YES header_row_written=YES")
            created += 1

        print(f"\nSUMMARY created={created} updated={updated} skipped={skipped}")
        return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
