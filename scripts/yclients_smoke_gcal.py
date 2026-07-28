#!/usr/bin/env python3
"""S7 smoke: create YCLIENTS record → mirror to GCal → cancel → delete from GCal.

Usage:
  cd /var/www/mywave && source venv/bin/activate
  set -a; source .env; set +a
  export YCLIENTS_ENABLED=1 YCLIENTS_WRITE_ENABLED=1 YCLIENTS_GCAL_MIRROR_ENABLED=1
  python scripts/yclients_smoke_gcal.py --date 2026-08-01
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=(date.today() + timedelta(days=4)).isoformat())
    args = parser.parse_args()

    os.environ.setdefault("DISABLE_TELEGRAM", "1")
    os.environ.setdefault("YCLIENTS_ENABLED", "1")
    os.environ.setdefault("YCLIENTS_WRITE_ENABLED", "1")
    os.environ.setdefault("YCLIENTS_GCAL_MIRROR_ENABLED", "1")

    from app import create_app

    app = create_app()
    with app.app_context():
        from app.services.booking.providers.yclients import get_yclients_provider
        from app.services.booking.yclients_sync import (
            find_calendar_event_by_record_id,
            sync_record_to_calendar,
        )

        provider = get_yclients_provider()
        raw = provider.fetch_available_slots_raw(args.date)
        if not raw:
            print("FAIL: no slots", args.date)
            return 1
        slot = raw[-1]
        time_str = str(slot.get("time"))[:5]
        dt = str(slot.get("datetime") or f"{args.date} {time_str}:00")
        if "T" in dt:
            dt_journal = dt.replace("T", " ")[:19]
        else:
            dt_journal = dt

        created = provider.create_booking(
            date_str=args.date,
            time_str=time_str,
            client_name="MyWave GCal Smoke",
            client_phone="79160000011",
            set_count=1,
            source="s7_gcal",
            internal_id=f"s7-gcal-{args.date}-{time_str.replace(':', '')}",
            datetime_iso=dt_journal,
            use_online=False,
        )
        rid = created.external_id
        print("created", rid, time_str)

        full = provider.get_record(rid)
        sync_payload = {
            "company_id": full.get("company_id"),
            "record_id": rid,
            "attendance": full.get("attendance"),
            "lifecycle": "waiting",
            "event_status": "create",
            "datetime": full.get("datetime") or full.get("date"),
            "seance_length": full.get("seance_length") or full.get("length"),
            "comment": full.get("comment") or "",
            "api_id": full.get("api_id") or "",
            "client": full.get("client") or {},
            "services": full.get("services") or [],
            "raw": full,
        }
        up = sync_record_to_calendar(sync_payload)
        print("upsert", up)
        found = find_calendar_event_by_record_id(rid)
        print("found_event", bool(found), (found or {}).get("id"), (found or {}).get("summary"))

        provider.cancel_booking(rid)
        full2 = provider.get_record(rid)
        sync_payload["attendance"] = full2.get("attendance")
        sync_payload["lifecycle"] = "cancelled"
        sync_payload["event_status"] = "update"
        sync_payload["raw"] = full2
        down = sync_record_to_calendar(sync_payload)
        print("delete_mirror", down)
        found2 = find_calendar_event_by_record_id(rid)
        print("found_after_cancel", found2)

        if up.get("mirror") not in ("inserted", "patched"):
            print("SMOKE GCAL FAIL upsert")
            return 1
        if down.get("mirror") != "deleted" and found2:
            print("SMOKE GCAL FAIL delete")
            return 1
        print("SMOKE GCAL PASS", rid)
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
