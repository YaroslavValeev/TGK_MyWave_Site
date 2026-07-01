#!/usr/bin/env python3
"""
Post-QA cleanup: remove confirmed test rows from Social Sheets tabs.

Usage:
  python tools/social_qa_cleanup.py --dry-run
  python tools/social_qa_cleanup.py --execute

No server/deploy/.env changes. Read-write only on Social_* tabs + backup sheet.
"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.config import GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID
from app.services.google_sheets_service import get_sheets_service, make_range
from app.services.social_schema import (
    SOCIAL_APPLICATIONS_SHEET,
    SOCIAL_AUDIT_LOG_SHEET,
    SOCIAL_SESSIONS_SHEET,
)

BACKUP_SHEET = "QA_CLEANUP_2026-07-01"

QA_APPLICATION_IDS = frozenset(
    {
        "soc_app_41d546e3b5aa47ea",
        "soc_app_e7be01a15ded4365",
    }
)
QA_SESSION_IDS = frozenset(
    {
        "soc_sess_800eaf177db24034",
        "soc_sess_e41e448019644a73",
    }
)
ALL_QA_IDS = QA_APPLICATION_IDS | QA_SESSION_IDS


def _read_sheet(service, spreadsheet_id: str, title: str) -> list[list[str]]:
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=make_range(title, "A1:ZZ1000"))
        .execute()
    )
    return result.get("values", [])


def _sheet_title_to_id(service, spreadsheet_id: str) -> dict[str, int]:
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    return {s["properties"]["title"]: s["properties"]["sheetId"] for s in meta.get("sheets", [])}


def _ensure_backup_sheet(service, spreadsheet_id: str, titles: dict[str, int]) -> None:
    if BACKUP_SHEET in titles:
        return
    service.spreadsheets().batchUpdate(
        spreadsheetId=spreadsheet_id,
        body={"requests": [{"addSheet": {"properties": {"title": BACKUP_SHEET}}}]},
    ).execute()
    print(f"created backup sheet: {BACKUP_SHEET}")


def _append_backup_rows(service, spreadsheet_id: str, rows: list[list[str]]) -> None:
    if not rows:
        return
    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=make_range(BACKUP_SHEET, "A1"),
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": rows},
    ).execute()


def _find_rows_to_delete_apps(values: list[list[str]]) -> list[int]:
    if not values:
        return []
    headers = [h.strip() for h in values[0]]
    try:
        idx = headers.index("application_id")
    except ValueError:
        idx = 0
    rows = []
    for i, row in enumerate(values[1:], start=2):
        app_id = row[idx].strip() if idx < len(row) else ""
        if app_id in QA_APPLICATION_IDS:
            rows.append(i)
    return sorted(rows, reverse=True)


def _find_rows_to_delete_sessions(values: list[list[str]]) -> list[int]:
    if not values:
        return []
    headers = [h.strip() for h in values[0]]
    try:
        idx = headers.index("session_id")
    except ValueError:
        idx = 0
    rows = []
    for i, row in enumerate(values[1:], start=2):
        sid = row[idx].strip() if idx < len(row) else ""
        if sid in QA_SESSION_IDS:
            rows.append(i)
    return sorted(rows, reverse=True)


def _find_rows_to_delete_audit(values: list[list[str]]) -> list[int]:
    if not values:
        return []
    rows = []
    for i, row in enumerate(values[1:], start=2):
        joined = " ".join(row)
        if any(qa_id in joined for qa_id in ALL_QA_IDS):
            rows.append(i)
    return sorted(rows, reverse=True)


def _delete_rows(service, spreadsheet_id: str, sheet_id: int, row_numbers_1based: list[int]) -> None:
  # row_numbers sorted descending
    requests = []
    for row_num in row_numbers_1based:
        start = row_num - 1
        requests.append(
            {
                "deleteDimension": {
                    "range": {
                        "sheetId": sheet_id,
                        "dimension": "ROWS",
                        "startIndex": start,
                        "endIndex": start + 1,
                    }
                }
            }
        )
    if requests:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id, body={"requests": requests}
        ).execute()


def _backup_row(source: str, row: list[str]) -> list[str]:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return [ts, source, *row]


def main() -> int:
    parser = argparse.ArgumentParser(description="Social QA Sheets cleanup")
    parser.add_argument("--execute", action="store_true", help="Apply changes (default: dry-run)")
    parser.add_argument("--dry-run", action="store_true", help="Show planned actions only")
    args = parser.parse_args()
    execute = args.execute and not args.dry_run
    if not args.execute and not args.dry_run:
        args.dry_run = True

    if not SPREADSHEET_ID:
        print("FAIL: SPREADSHEET_ID not set")
        return 1
    if not os.path.isfile(GOOGLE_SERVICE_ACCOUNT_FILE or ""):
        print(f"FAIL: service account not found: {GOOGLE_SERVICE_ACCOUNT_FILE}")
        return 1

    service = get_sheets_service()
    sid = SPREADSHEET_ID
    titles = _sheet_title_to_id(service, sid)

    plan: dict[str, list[int]] = {}
    backup_rows: list[list[str]] = []

    apps_values = _read_sheet(service, sid, SOCIAL_APPLICATIONS_SHEET)
    sess_values = _read_sheet(service, sid, SOCIAL_SESSIONS_SHEET)
    audit_values = _read_sheet(service, sid, SOCIAL_AUDIT_LOG_SHEET)

    apps_rows = _find_rows_to_delete_apps(apps_values)
    sess_rows = _find_rows_to_delete_sessions(sess_values)
    audit_rows = _find_rows_to_delete_audit(audit_values)

    plan[SOCIAL_APPLICATIONS_SHEET] = sorted(apps_rows)
    plan[SOCIAL_SESSIONS_SHEET] = sorted(sess_rows)
    plan[SOCIAL_AUDIT_LOG_SHEET] = sorted(audit_rows)

    for row_num in plan[SOCIAL_APPLICATIONS_SHEET]:
        backup_rows.append(_backup_row(SOCIAL_APPLICATIONS_SHEET, apps_values[row_num - 1]))
    for row_num in plan[SOCIAL_SESSIONS_SHEET]:
        backup_rows.append(_backup_row(SOCIAL_SESSIONS_SHEET, sess_values[row_num - 1]))
    for row_num in plan[SOCIAL_AUDIT_LOG_SHEET]:
        backup_rows.append(_backup_row(SOCIAL_AUDIT_LOG_SHEET, audit_values[row_num - 1]))

    print("=== Social QA cleanup plan ===")
    print(f"spreadsheet_tail={sid[-8:]}")
    print(f"mode={'EXECUTE' if execute else 'DRY-RUN'}")
    for sheet, rows in plan.items():
        print(f"{sheet}: delete rows {rows}")
    print(f"backup_rows={len(backup_rows)} -> {BACKUP_SHEET}")

    if not any(plan.values()):
        print("OK: nothing to delete")
        return 0

    if not execute:
        print("DRY-RUN complete. Re-run with --execute to apply.")
        return 0

    _ensure_backup_sheet(service, sid, titles)
    titles = _sheet_title_to_id(service, sid)
    header = [["backed_up_at", "source_sheet"]]
    existing = _read_sheet(service, sid, BACKUP_SHEET)
    if not existing:
        _append_backup_rows(service, sid, header)
    _append_backup_rows(service, sid, backup_rows)

    _delete_rows(service, sid, titles[SOCIAL_APPLICATIONS_SHEET], apps_rows)
    _delete_rows(service, sid, titles[SOCIAL_SESSIONS_SHEET], sess_rows)
    _delete_rows(service, sid, titles[SOCIAL_AUDIT_LOG_SHEET], audit_rows)

    print("CLEANUP=PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
