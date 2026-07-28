#!/usr/bin/env python3
"""S6 controlled write smoke: create one test record, verify, cancel.

Usage:
  cd /var/www/mywave && source venv/bin/activate
  set -a; source .env; set +a
  export YCLIENTS_ENABLED=1 YCLIENTS_WRITE_ENABLED=1
  python scripts/yclients_smoke_write.py --date 2026-07-31 --keep  # keep without cancel
  python scripts/yclients_smoke_write.py --date 2026-07-31         # create + cancel
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=(date.today() + timedelta(days=3)).isoformat())
    parser.add_argument("--keep", action="store_true", help="Do not cancel after create")
    parser.add_argument("--phone", default="79160000001")
    parser.add_argument("--name", default="MyWave S6 Smoke")
    args = parser.parse_args()

    os.environ.setdefault("YCLIENTS_ENABLED", "1")
    os.environ.setdefault("YCLIENTS_READ_ONLY_ENABLED", "1")
    if os.environ.get("YCLIENTS_WRITE_ENABLED", "0").strip() not in ("1", "true", "yes", "on"):
        print("ERROR: set YCLIENTS_WRITE_ENABLED=1")
        return 1

    from app.services.booking.providers.yclients import (
        YclientsApiError,
        YclientsNotConfiguredError,
        get_yclients_provider,
    )

    provider = get_yclients_provider()
    try:
        raw_slots = provider.fetch_available_slots_raw(args.date)
    except (YclientsNotConfiguredError, YclientsApiError) as exc:
        print("FAIL slots:", exc)
        return 1

    if not raw_slots:
        print(f"FAIL: no free slots on {args.date}")
        return 1

    slot = raw_slots[-1]  # last slot of day — less collision risk
    time_str = str(slot.get("time") or "")[:5]
    datetime_iso = str(slot.get("datetime") or f"{args.date} {time_str}:00")
    print("using_slot", args.date, time_str, datetime_iso)

    try:
        created = provider.create_booking(
            date_str=args.date,
            time_str=time_str,
            client_name=args.name,
            client_phone=args.phone,
            client_email="noreply@mywavewake.ru",
            set_count=1,
            source="s6_smoke",
            internal_id=f"s6-smoke-{args.date}-{time_str.replace(':', '')}",
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

    try:
        fetched = provider.get_record(record_id)
        print(
            "fetched",
            fetched.get("id"),
            fetched.get("date") or fetched.get("datetime"),
            "attendance=",
            fetched.get("attendance"),
            "comment=",
            (fetched.get("comment") or "")[:80],
        )
    except YclientsApiError as exc:
        print("WARN get_record:", exc)

    if args.keep:
        print("SMOKE WRITE PASS (kept)", record_id)
        return 0

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

    print("SMOKE WRITE PASS (created+cancelled)", record_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
