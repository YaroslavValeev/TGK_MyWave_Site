#!/usr/bin/env python3
"""Cron/ops entry: import camps from MyWaveTour into local DB."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync camps from MyWaveTour feed")
    parser.add_argument(
        "--updated-since",
        default=None,
        help="ISO datetime for incremental sync (optional)",
    )
    args = parser.parse_args()

    from datetime import datetime

    from app import create_app
    from app.config.camp_features import is_camp_import_enabled
    from app.services.camps.import_service import sync_camps_from_tour

    app = create_app()
    with app.app_context():
        if not is_camp_import_enabled():
            print("camp_sync: CAMP_IMPORT_ENABLED=0 — skip")
            return 0
        since = datetime.fromisoformat(args.updated_since) if args.updated_since else None
        try:
            stats = sync_camps_from_tour(updated_since=since)
        except Exception as exc:
            from app.services.camps.tour_client import TourCampFetchError

            if isinstance(exc, TourCampFetchError):
                app.logger.error(
                    "camp_sync_failed",
                    extra={"status_code": exc.status_code, "kind": exc.kind, "error": str(exc)},
                )
            else:
                app.logger.exception("camp_sync_failed")
            print(f"camp_sync: failed — {exc}")
            return 1
        app.logger.info("camp_sync_done", extra=stats)
        print(f"camp_sync: {stats}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
