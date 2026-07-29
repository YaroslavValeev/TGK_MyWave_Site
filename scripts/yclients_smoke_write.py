#!/usr/bin/env python3
"""Controlled YClients write smoke: create test record(s), verify length/qty, cancel.

Usage:
  cd /var/www/mywave && source venv/bin/activate
  set -a; source .env; set +a
  python scripts/yclients_smoke_write.py --date 2026-08-05 --sets 1
  python scripts/yclients_smoke_write.py --date 2026-08-05 --sets 3
  python scripts/yclients_smoke_write.py --date 2026-08-05 --sets 3 --keep
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _service_amount(record: dict) -> int | None:
    services = record.get("services") or []
    if not services:
        return None
    first = services[0] if isinstance(services[0], dict) else {}
    raw = first.get("amount")
    if raw is None:
        return 1 if first.get("id") else None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=(date.today() + timedelta(days=3)).isoformat())
    parser.add_argument("--sets", type=int, default=1, help="Boat set_count (N×30 min + amount=N)")
    parser.add_argument("--keep", action="store_true", help="Do not cancel after create")
    parser.add_argument("--phone", default="79160000001")
    parser.add_argument("--name", default="MyWave YC Smoke")
    args = parser.parse_args()

    sets = max(1, int(args.sets or 1))
    os.environ.setdefault("YCLIENTS_ENABLED", "1")
    os.environ.setdefault("YCLIENTS_READ_ONLY_ENABLED", "1")
    if os.environ.get("YCLIENTS_WRITE_ENABLED", "0").strip().lower() not in (
        "1",
        "true",
        "yes",
        "on",
    ):
        print("ERROR: set YCLIENTS_WRITE_ENABLED=1 in .env")
        return 1

    from app.config.booking_schedule import boat_slot_duration_minutes
    from app.services.booking.providers.yclients import (
        YclientsApiError,
        YclientsNotConfiguredError,
        get_yclients_provider,
    )

    slot_min = boat_slot_duration_minutes()
    expect_sec = sets * slot_min * 60

    provider = get_yclients_provider()
    try:
        raw_slots = provider.fetch_available_slots_raw(args.date)
    except (YclientsNotConfiguredError, YclientsApiError) as exc:
        print("FAIL slots:", exc)
        return 1

    if not raw_slots:
        print(f"FAIL: no free slots on {args.date}")
        return 1

    # Prefer late slots; for multi-set need room — use early enough time if possible
    slot = raw_slots[max(0, len(raw_slots) - max(sets, 1))]
    if sets > 1 and len(raw_slots) >= sets:
        slot = raw_slots[-(sets)]
    time_str = str(slot.get("time") or "")[:5]
    datetime_iso = str(slot.get("datetime") or f"{args.date} {time_str}:00")
    print("using_slot", args.date, time_str, "sets=", sets, "expect_seance_sec=", expect_sec)

    try:
        created = provider.create_booking(
            date_str=args.date,
            time_str=time_str,
            client_name=args.name,
            client_phone=args.phone,
            client_email="noreply@mywavewake.ru",
            set_count=sets,
            source="s6_smoke",
            internal_id=f"s6-smoke-{args.date}-{time_str.replace(':', '')}-x{sets}",
            datetime_iso=datetime_iso.replace("T", " ")[:19]
            if "T" in datetime_iso
            else datetime_iso,
            use_online=False,
        )
    except (YclientsNotConfiguredError, YclientsApiError) as exc:
        print("FAIL create:", exc)
        if isinstance(exc, YclientsApiError) and exc.payload:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2)[:2000])
        return 1

    record_id = created.external_id
    print("created_record_id=", record_id)
    print("create_status=", created.status)

    ok = True
    try:
        fetched = provider.get_record(record_id)
        seance = fetched.get("seance_length") or fetched.get("length")
        amount = _service_amount(fetched)
        print(
            "fetched id=",
            fetched.get("id"),
            "datetime=",
            fetched.get("date") or fetched.get("datetime"),
            "seance_length=",
            seance,
            "service_amount=",
            amount,
            "attendance=",
            fetched.get("attendance"),
            "comment=",
            (fetched.get("comment") or "")[:80],
        )
        try:
            seance_i = int(seance) if seance is not None else None
        except (TypeError, ValueError):
            seance_i = None
        if seance_i != expect_sec:
            print(f"FAIL: seance_length want {expect_sec}, got {seance_i}")
            ok = False
        if amount != sets:
            print(f"FAIL: service amount want {sets}, got {amount}")
            ok = False
        if ok:
            print(f"VERIFY PASS: {sets} set(s) → {expect_sec}s + amount={sets}")
    except YclientsApiError as exc:
        print("WARN get_record:", exc)
        ok = False

    if args.keep:
        print("SMOKE WRITE PASS (kept)" if ok else "SMOKE WRITE KEEP (verify FAIL)", record_id)
        return 0 if ok else 2

    try:
        provider.cancel_booking(record_id)
        print("cancelled_record_id=", record_id)
        after = provider.get_record(record_id)
        print("after_cancel attendance=", after.get("attendance"))
    except YclientsApiError as exc:
        print("FAIL cancel:", exc)
        if exc.payload:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2)[:1000])
        return 1

    if not ok:
        print("SMOKE WRITE FAIL (created+cancelled but verify mismatch)", record_id)
        return 2
    print("SMOKE WRITE PASS (created+verified+cancelled)", record_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
