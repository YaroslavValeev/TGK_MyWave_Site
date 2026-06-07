#!/usr/bin/env python3
"""Seed Schedule rows for S5 part A (idempotent, staging Sheet only)."""

from __future__ import annotations

import os
import sys
from datetime import datetime

STAGING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(STAGING_DIR, "..", ".."))
for p in (ROOT, STAGING_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from _staging_env import assert_staging_spreadsheet, load_staging_dotenv

DATE = os.environ.get("S5_DATE_BOAT_GYM", "2026-06-20")
S5_SCHEDULE_TIMES = ("14:00", "14:30")


def main() -> int:
    load_staging_dotenv()
    from app import create_app
    from app.services.google_sheets_service import append_record, read_records

    dow = datetime.strptime(DATE, "%Y-%m-%d").strftime("%A").lower()
    app = create_app()
    with app.app_context():
        sid = app.config["SPREADSHEET_ID"]
        assert_staging_spreadsheet(sid, script="s5_seed")
        rows = read_records(sid, "Schedule")
        existing = {
            (r.get("day_of_week", "").strip().lower(), r.get("time", "").strip()[:5])
            for r in rows
        }
        for t in S5_SCHEDULE_TIMES:
            key = (dow, t)
            if key not in existing:
                append_record(sid, "Schedule", [dow, t, "4"])
                print("schedule_added", dow, t)
            else:
                print("schedule_exists", dow, t)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
