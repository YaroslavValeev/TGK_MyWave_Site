#!/usr/bin/env python3
"""Cron entry: process Online Coaching follow-up reminders."""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Online Coaching reminders")
    parser.add_argument("--dry-run", action="store_true", help="List due reminders without sending")
    args = parser.parse_args()

    from app import create_app
    from app.config.online_coaching_features import is_online_coaching_reminders_enabled
    from app.services.online_coaching_reminders import process_due_reminders

    app = create_app()
    with app.app_context():
        if not is_online_coaching_reminders_enabled():
            print("online_coaching_reminders: disabled")
            return 0
        result = process_due_reminders(dry_run=args.dry_run)
        print(
            "online_coaching_reminders:",
            f"due={result['due_count']}",
            f"processed={len(result['processed'])}",
            f"skipped={len(result['skipped'])}",
            f"dry_run={result['dry_run']}",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
