#!/usr/bin/env python3
"""S5 — canonical travel buffer smoke (120 min). Run on staging host."""

from __future__ import annotations

import os
import subprocess
import sys

STAGING_DIR = os.path.dirname(os.path.abspath(__file__))
if STAGING_DIR not in sys.path:
    sys.path.insert(0, STAGING_DIR)

from _client import StagingClient

DATE_B = os.environ.get("S5_DATE_GYM_BOAT", "2026-06-13")
DATE_A = os.environ.get("S5_DATE_BOAT_GYM", "2026-06-20")


def _slot_available(slots: dict[str, dict], time_str: str) -> bool | None:
    row = slots.get(time_str)
    if row is None:
        return None
    return bool(row.get("available"))


def _seed_schedule_subprocess() -> None:
    env = os.environ.copy()
    env["S5_DATE_BOAT_GYM"] = DATE_A
    subprocess.run(
        [sys.executable, os.path.join(STAGING_DIR, "s5_seed_schedule.py")],
        env=env,
        check=True,
    )


def main() -> int:
    _seed_schedule_subprocess()

    client = StagingClient()
    failures: list[str] = []

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
