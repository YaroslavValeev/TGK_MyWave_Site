#!/usr/bin/env python3
"""S9 — orphan Workouts without Client_Workouts pair (staging Sheet guard)."""

from __future__ import annotations

import os
import sys

STAGING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(STAGING_DIR, "..", ".."))
for p in (ROOT, STAGING_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from _staging_env import assert_staging_spreadsheet, load_staging_dotenv


def main() -> int:
    load_staging_dotenv()
    from app import create_app
    from app.services.google_sheets_service import read_records

    app = create_app()
    with app.app_context():
        sid = app.config["SPREADSHEET_ID"]
        assert_staging_spreadsheet(sid, script="s9")

        workouts = read_records(sid, "Workouts")
        links = read_records(sid, "Client_Workouts")
        linked = {str(r.get("workout_id", "")).strip() for r in links}
        orphans = []
        for w in workouts:
            wid = str(w.get("workout_id", "")).strip()
            status = str(w.get("workout_status", "")).strip().lower()
            if not wid or status in ("отменено", "cancelled", "canceled"):
                continue
            if wid not in linked:
                orphans.append(wid[-12:])

    print("orphan_count", len(orphans))
    for tail in orphans[:20]:
        print("orphan_tail", tail)
    if orphans:
        print("S9_fail")
        return 1
    print("S9_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
