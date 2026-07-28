#!/usr/bin/env python3
"""Discover YCLIENTS company / staff / services IDs (read-only).

Usage (on server):
  cd /var/www/mywave
  source venv/bin/activate
  set -a; source .env; set +a
  export YCLIENTS_ENABLED=1 YCLIENTS_READ_ONLY_ENABLED=1
  python scripts/yclients_discover.py
"""

from __future__ import annotations

import json
import os
import sys

# Ensure app import path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    os.environ.setdefault("YCLIENTS_ENABLED", "1")
    os.environ.setdefault("YCLIENTS_READ_ONLY_ENABLED", "1")

    from app.services.booking.providers.yclients import (
        YclientsApiError,
        YclientsNotConfiguredError,
        get_yclients_provider,
    )

    provider = get_yclients_provider()
    try:
        company = provider.get_company()
        staff = provider.list_staff()
        services = provider.list_services()
    except (YclientsNotConfiguredError, YclientsApiError) as exc:
        print(f"ERROR: {exc}")
        if isinstance(exc, YclientsApiError) and exc.payload:
            print(json.dumps(exc.payload, ensure_ascii=False, indent=2))
        return 1

    company_data = company.get("data") if isinstance(company.get("data"), dict) else company
    print("=== COMPANY ===")
    print(
        json.dumps(
            {
                "id": company_data.get("id"),
                "title": company_data.get("title"),
                "timezone": company_data.get("timezone"),
                "timezone_name": company_data.get("timezone_name"),
                "city": company_data.get("city"),
                "address": company_data.get("address"),
            },
            ensure_ascii=False,
            indent=2,
        )
    )

    print("\n=== STAFF ===")
    for item in staff:
        print(
            json.dumps(
                {
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "bookable": item.get("bookable"),
                    "specialization": item.get("specialization"),
                },
                ensure_ascii=False,
            )
        )

    print("\n=== SERVICES ===")
    for item in services:
        print(
            json.dumps(
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "duration": item.get("duration") or item.get("seance_length"),
                    "price_min": item.get("price_min"),
                    "active": item.get("active"),
                },
                ensure_ascii=False,
            )
        )

    print("\n=== ENV SUGGESTIONS ===")
    if staff:
        print(f"YCLIENTS_STAFF_ID={staff[0].get('id')}")
    if services:
        ids = ",".join(str(s.get("id")) for s in services if s.get("id"))
        print(f"YCLIENTS_SERVICE_IDS={ids}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
