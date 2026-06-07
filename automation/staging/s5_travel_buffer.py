#!/usr/bin/env python3
"""S5 — canonical travel buffer smoke (120 min). Run on staging host."""

from __future__ import annotations

import os
import sys
from datetime import datetime

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
STAGING_DIR = os.path.dirname(__file__)
for p in (ROOT, STAGING_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from _client import StagingClient

# Saturday — gym 10:00 in Schedule seed
DATE_B = os.environ.get("S5_DATE_GYM_BOAT", "2026-06-13")
# Next Saturday — clean day for boat→gym
DATE_A = os.environ.get("S5_DATE_BOAT_GYM", "2026-06-20")
S5_SCHEDULE_TIMES = ("14:00", "14:30")


def _day_of_week(date_str: str) -> str:
    return datetime.strptime(date_str, "%Y-%m-%d").strftime("%A").lower()


def ensure_s5_schedule_rows(date_str: str) -> None:
    """Add 14:00 / 14:30 to Schedule for S5 part A if missing (staging only)."""
    from app import create_app
    from app.services.google_sheets_service import append_record, read_records

    dow = _day_of_week(date_str)
    app = create_app()
    with app.app_context():
        sid = app.config["SPREADSHEET_ID"]
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


def _slot_available(slots: dict[str, dict], time_str: str) -> bool | None:
    row = slots.get(time_str)
    if row is None:
        return None
    return bool(row.get("available"))


def main() -> int:
    client = StagingClient()
    failures: list[str] = []

    # --- Part B: gym 10:00 → boat 12:00 blocked, 13:30 allowed ---
    print(f"S5_part_B date={DATE_B}")
    code, body = client.book(
        date=DATE_B,
        time="10:00",
        name="S5 Gym Anchor",
        phone="+79990005001",
        service_type="gym",
    )
    print("book_gym_10", code, body.get("status") or body.get("error"))
    if code not in (200, 201):
        failures.append(f"gym_10_book_http_{code}")

    boat = client.slot_map(DATE_B, "boat")
    b12 = _slot_available(boat, "12:00")
    b1330 = _slot_available(boat, "13:30")
    print("boat_12_available", b12, "boat_1330_available", b1330)
    if b12 is not False:
        failures.append("boat_12_should_be_blocked")
    if b1330 is not True:
        failures.append("boat_1330_should_be_available")

    # --- Part A: boat 12:00 → gym 14:00 blocked, 14:30 allowed ---
    ensure_s5_schedule_rows(DATE_A)
    print(f"S5_part_A date={DATE_A}")

    code, body = client.book(
        date=DATE_A,
        time="12:00",
        name="S5 Boat Anchor",
        phone="+79990005002",
        service_type="boat",
        set_count=1,
    )
    print("book_boat_12", code, body.get("status") or body.get("error"))
    if code not in (200, 201):
        failures.append(f"boat_12_book_http_{code}")

    gym = client.slot_map(DATE_A, "gym")
    g14 = _slot_available(gym, "14:00")
    g1430 = _slot_available(gym, "14:30")
    print("gym_14_available", g14, "gym_1430_available", g1430)
    if g14 is not False:
        failures.append("gym_14_should_be_blocked")
    if g1430 is not True:
        failures.append("gym_1430_should_be_available")

    if failures:
        print("S5_fail", failures)
        return 1
    print("S5_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
