#!/usr/bin/env python3
"""S5 travel buffer smoke via Flask test_client (staging .env, isolated process)."""

from __future__ import annotations

import json
import os
import sys
import time

STAGING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(STAGING_DIR, "..", ".."))
for p in (ROOT, STAGING_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from _staging_env import assert_staging_spreadsheet, load_staging_dotenv

DATE_B = os.environ.get("S5_DATE_GYM_BOAT", "2026-06-13")
DATE_A = os.environ.get("S5_DATE_BOAT_GYM", "2026-06-20")
S5_SCHEDULE_TIMES = ("14:00", "14:30")


def _unique_phone(tag: str) -> str:
    """RU mobile: +7 + 10 digits (e.g. +79991234567)."""
    run = os.environ.get("S5_RUN_ID") or str(int(time.time()))
    suffix = abs(hash(f"{tag}:{run}")) % 1_000_000_000
    return f"+79{suffix:09d}"


def _ensure_schedule(app, date_str: str) -> None:
    from datetime import datetime

    from app.services.google_sheets_service import append_record, read_records

    dow = datetime.strptime(date_str, "%Y-%m-%d").strftime("%A").lower()
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


def _slot_available(slots: list[dict], time_str: str) -> bool | None:
    row = next((s for s in slots if s.get("time") == time_str), None)
    if row is None:
        return None
    return bool(row.get("available"))


def _boat_slot_blocked(slots: list[dict], time_str: str) -> bool:
    """Phase 2 boat grid omits blocked slots (not listed), not available=false."""
    row = next((s for s in slots if s.get("time") == time_str), None)
    if row is None:
        return True
    return not bool(row.get("available"))


def _boat_slot_available(slots: list[dict], time_str: str) -> bool:
    row = next((s for s in slots if s.get("time") == time_str), None)
    return row is not None and bool(row.get("available"))


def _gym_slot_blocked(slots: list[dict], time_str: str) -> bool:
    row = next((s for s in slots if s.get("time") == time_str), None)
    if row is None:
        return False  # missing schedule row — fail loud elsewhere
    return not bool(row.get("available"))


def _gym_slot_available(slots: list[dict], time_str: str) -> bool:
    row = next((s for s in slots if s.get("time") == time_str), None)
    return row is not None and bool(row.get("available"))


def _response_body(resp) -> dict:
    try:
        return resp.get_json(silent=True) or {}
    except Exception:
        return {"raw": (resp.data or b"")[:500].decode("utf-8", "replace")}


def _book(client, payload: dict) -> tuple[int, dict]:
    csrf_resp = client.get("/api/csrf-token")
    token = (_response_body(csrf_resp).get("csrf_token") or "").strip()
    if not token:
        return csrf_resp.status_code, {"error": "csrf_token_missing"}
    # csrf_token only in header — BookingSchema rejects unknown JSON fields
    resp = client.post(
        "/api/calendar/book",
        json=payload,
        headers={"X-CSRFToken": token},
    )
    return resp.status_code, _response_body(resp)


def _slots(client, date: str, service: str) -> list[dict]:
    resp = client.get(f"/api/calendar/slots/{date}?service={service}")
    data = _response_body(resp)
    if isinstance(data, list):
        return data
    return []


def _log_book(label: str, code: int, body: dict) -> None:
    err = body.get("error") or body.get("message")
    details = body.get("details")
    print(label, code, err or json.dumps(body, ensure_ascii=False)[:300])
    if details:
        print(f"{label}_details", details)


def main() -> int:
    load_staging_dotenv()
    from app import create_app

    app = create_app()
    _ensure_schedule(app, DATE_A)

    client = app.test_client()
    failures: list[str] = []
    part_b_ok = False
    part_a_ok = False

    phone_b = os.environ.get("S5_PHONE_GYM") or _unique_phone("gym")
    phone_a = os.environ.get("S5_PHONE_BOAT") or _unique_phone("boat")

    print(f"S5_part_B date={DATE_B} phone={phone_b}")
    code, body = _book(
        client,
        {
            "date": DATE_B,
            "time": "10:00",
            "name": "S5 Gym Anchor",
            "phone": phone_b,
            "service_type": "gym",
        },
    )
    _log_book("book_gym_10", code, body)
    part_b_failures: list[str] = []
    if code not in (200, 201):
        part_b_failures.append(f"gym_10_book_http_{code}")
    else:
        boat = _slots(client, DATE_B, "boat")
        b12_blocked = _boat_slot_blocked(boat, "12:00")
        b1330_ok = _boat_slot_available(boat, "13:30")
        print("boat_12_blocked", b12_blocked, "boat_1330_available", b1330_ok)
        if not b12_blocked:
            part_b_failures.append("boat_12_should_be_blocked")
        if not b1330_ok:
            part_b_failures.append("boat_1330_should_be_available")

    if part_b_failures:
        failures.extend(part_b_failures)
    else:
        part_b_ok = True
        print("S5_part_B_ok")

    print(f"S5_part_A date={DATE_A} phone={phone_a}")
    code, body = _book(
        client,
        {
            "date": DATE_A,
            "time": "12:00",
            "name": "S5 Boat Anchor",
            "phone": phone_a,
            "service_type": "boat",
            "set_count": 1,
        },
    )
    _log_book("book_boat_12", code, body)
    part_a_failures: list[str] = []
    if code not in (200, 201):
        part_a_failures.append(f"boat_12_book_http_{code}")
    else:
        gym = _slots(client, DATE_A, "gym")
        g14_blocked = _gym_slot_blocked(gym, "14:00")
        g1430_ok = _gym_slot_available(gym, "14:30")
        print("gym_14_blocked", g14_blocked, "gym_1430_available", g1430_ok)
        if not g14_blocked:
            part_a_failures.append("gym_14_should_be_blocked")
        if not g1430_ok:
            part_a_failures.append("gym_1430_should_be_available")

    if part_a_failures:
        failures.extend(part_a_failures)
    else:
        part_a_ok = True
        print("S5_part_A_ok")

    if failures:
        print("S5_fail", failures)
        return 1
    if part_b_ok and part_a_ok:
        print("S5_ok")
        return 0
    print("S5_fail incomplete_parts", {"part_b_ok": part_b_ok, "part_a_ok": part_a_ok})
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
