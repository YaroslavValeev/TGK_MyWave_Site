#!/usr/bin/env python3
"""S5 read-only smoke against live YCLIENTS (no writes).

Usage:
  cd /var/www/mywave && source venv/bin/activate
  set -a; source .env; set +a
  export YCLIENTS_ENABLED=1 YCLIENTS_READ_ONLY_ENABLED=1 YCLIENTS_WRITE_ENABLED=0
  python scripts/yclients_smoke_read.py --date 2026-07-30
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
    parser.add_argument(
        "--date",
        default=(date.today() + timedelta(days=1)).isoformat(),
        help="YYYY-MM-DD for book_times",
    )
    args = parser.parse_args()

    os.environ.setdefault("YCLIENTS_ENABLED", "1")
    os.environ.setdefault("YCLIENTS_READ_ONLY_ENABLED", "1")
    os.environ["YCLIENTS_WRITE_ENABLED"] = "0"

    from app.config.yclients_config import (
        yclients_company_id,
        yclients_default_service_id,
        yclients_partner_token,
        yclients_staff_id,
        yclients_user_token,
    )
    from app.services.booking.providers.yclients import (
        YclientsApiError,
        YclientsNotConfiguredError,
        get_yclients_provider,
    )

    print("company_id=", yclients_company_id())
    print("partner_token=", "yes" if yclients_partner_token() else "MISSING")
    print("user_token=", "yes" if yclients_user_token() else "MISSING")
    print("staff_id=", yclients_staff_id() or "MISSING")
    print("default_service_id=", yclients_default_service_id() or "MISSING")

    provider = get_yclients_provider()
    try:
        company = provider.get_company()
        staff = provider.list_staff()
        services = provider.list_services()
        slots = provider.fetch_available_slots(args.date)
    except (YclientsNotConfiguredError, YclientsApiError) as exc:
        print("SMOKE FAIL:", exc)
        if isinstance(exc, YclientsApiError) and exc.payload:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2)[:2000])
        return 1

    print("company_ok=", bool(company))
    print("staff_count=", len(staff))
    print("services_count=", len(services))
    print("slots_date=", args.date, "count=", len(slots))
    for slot in slots[:12]:
        print(f"  slot {slot.start_time} ({slot.duration_minutes}m)")

    records_ok = False
    try:
        records = provider.list_records(
            start_date=args.date,
            end_date=args.date,
            count=20,
        )
        records_ok = True
        print("records_count=", len(records))
        for rec in records[:5]:
            print(
                "  record",
                rec.get("id"),
                rec.get("date") or rec.get("datetime"),
                "attendance=",
                rec.get("attendance"),
            )
    except YclientsApiError as exc:
        print("records_WARN:", exc, "(нужно подключить приложение к филиалу или User token владельца)")
        if exc.payload:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2)[:500])

    if not slots and not records_ok:
        print("SMOKE FAIL: no slots and no records access")
        return 1

    print("SMOKE PASS" + ("" if records_ok else " (slots OK; records pending permissions)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
