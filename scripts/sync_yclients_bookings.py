"""Ops: reconcile YCLIENTS records with Google Calendar."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync YCLIENTS bookings to Google Calendar")
    parser.add_argument("--days-back", type=int, default=1)
    parser.add_argument("--days-forward", type=int, default=14)
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument("--apply", action="store_true", help="Disable dry-run / write to GCal")
    parser.add_argument("--include-cancelled", action="store_true")
    args = parser.parse_args()
    dry_run = not args.apply

    # Ensure app context for Google + config
    os.environ.setdefault("DISABLE_TELEGRAM", "1")
    from app import create_app

    app = create_app()
    with app.app_context():
        from app.config.yclients_config import (
            is_yclients_enabled,
            is_yclients_gcal_mirror_enabled,
            is_yclients_read_enabled,
        )
        from app.services.booking.providers.yclients import (
            YclientsApiError,
            YclientsNotConfiguredError,
            get_yclients_provider,
            parse_attendance_status,
        )
        from app.services.booking.yclients_sync import sync_record_to_calendar

        if not is_yclients_enabled() or not is_yclients_read_enabled():
            print("yclients_sync: YCLIENTS read disabled — skip")
            return 0

        print(
            "yclients_sync: gcal_mirror=",
            is_yclients_gcal_mirror_enabled(),
            "dry_run=",
            dry_run,
        )

        start = (date.today() - timedelta(days=args.days_back)).isoformat()
        end = (date.today() + timedelta(days=args.days_forward)).isoformat()
        provider = get_yclients_provider()
        try:
            records = provider.list_records(start_date=start, end_date=end, count=200)
        except (YclientsNotConfiguredError, YclientsApiError) as exc:
            print(f"yclients_sync: {exc}")
            return 1

        print(f"yclients_sync: fetched={len(records)} range={start}..{end}")
        synced = 0
        for rec in records:
            if not isinstance(rec, dict):
                continue
            lifecycle = parse_attendance_status(
                rec.get("attendance"), deleted=bool(rec.get("deleted"))
            )
            if lifecycle in ("cancelled", "deleted") and not args.include_cancelled:
                continue
            payload = {
                "company_id": rec.get("company_id"),
                "record_id": rec.get("id"),
                "attendance": rec.get("attendance"),
                "deleted": rec.get("deleted"),
                "lifecycle": lifecycle,
                "event_status": "reconcile",
                "datetime": rec.get("datetime") or rec.get("date"),
                "seance_length": rec.get("seance_length") or rec.get("length"),
                "client": rec.get("client") or {},
                "services": rec.get("services") or [],
                "comment": rec.get("comment") or "",
                "api_id": rec.get("api_id") or "",
                "raw": rec,
            }
            if dry_run:
                print(
                    json.dumps(
                        {
                            "record_id": payload["record_id"],
                            "lifecycle": payload["lifecycle"],
                            "datetime": payload["datetime"],
                            "comment": (payload["comment"] or "")[:60],
                        },
                        ensure_ascii=False,
                    )
                )
                continue
            result = sync_record_to_calendar(payload)
            synced += 1
            print(json.dumps(result, ensure_ascii=False))

        print(f"yclients_sync: done synced={synced}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
