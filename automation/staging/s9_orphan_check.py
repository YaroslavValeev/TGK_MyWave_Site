#!/usr/bin/env python3
"""S9 — orphan Workouts without Client_Workouts pair. Run on staging host."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


def main() -> int:
    from app import create_app
    from app.services.google_sheets_service import read_records

    app = create_app()
    with app.app_context():
        sid = app.config["SPREADSHEET_ID"]
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
        return 1
    print("S9_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
