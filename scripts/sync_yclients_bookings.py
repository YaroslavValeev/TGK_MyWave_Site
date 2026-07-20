"""Ops: reconcile YCLIENTS records with Google Calendar."""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync YCLIENTS bookings to Google Calendar")
    parser.add_argument("--days-back", type=int, default=1)
    parser.add_argument("--days-forward", type=int, default=90)
    args = parser.parse_args()

    from app import create_app
    from app.config.yclients_config import is_yclients_enabled
    from app.services.booking.providers.yclients import (
        YclientsNotConfiguredError,
        get_yclients_provider,
    )

    app = create_app()
    with app.app_context():
        if not is_yclients_enabled():
            print("yclients_sync: YCLIENTS_ENABLED=0 — skip")
            return 0
        provider = get_yclients_provider()
        try:
            provider._require_enabled()
        except YclientsNotConfiguredError as exc:
            print(f"yclients_sync: {exc}")
            return 1
        print(
            f"yclients_sync: stub days_back={args.days_back} "
            f"days_forward={args.days_forward} (awaiting API credentials)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
