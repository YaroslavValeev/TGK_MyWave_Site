#!/usr/bin/env python3
"""Production-safe notification delivery diagnostics (no secrets printed)."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _flag(name: str) -> str:
    return "set" if (os.getenv(name) or "").strip() else "missing"


def main() -> int:
    keys = (
        "NOTIFICATION_BOT_TOKEN",
        "TELEGRAM_BOT_TOKEN",
        "ADMIN_CHAT_ID",
        "TELEGRAM_CHAT_ID",
        "TRAINER_CHAT_ID",
        "SPREADSHEET_ID",
        "PRODUCT_LEADS_SHEET_NAME",
    )
    print("=== MyWave notification diagnostics (sanitized) ===")
    for key in keys:
        print(f"{key}: {_flag(key)}")

    has_token = bool(
        (os.getenv("NOTIFICATION_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN") or "").strip()
    )
    has_chat = bool(
        (
            os.getenv("ADMIN_CHAT_ID")
            or os.getenv("TELEGRAM_CHAT_ID")
            or os.getenv("TRAINER_CHAT_ID")
            or ""
        ).strip()
    )
    print()
    if has_token and has_chat:
        print("telegram_delivery: credentials_present (live send not attempted)")
    else:
        print("telegram_delivery: skipped_missing_credentials")
        print("  → product/service leads still save; check app logs:")
        print("     telegram_notify_skipped | application_notify_result | product_lead_saved")
    print()
    print("service_leads_path: POST /analytics/log → analytics sheet + notify_service_lead_from_analytics")
    print("product_leads_path: POST /shop/api/product-request → Product_Leads + notify_new_application")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
