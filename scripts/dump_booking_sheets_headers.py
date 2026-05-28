#!/usr/bin/env python3
"""Dump Google Sheets headers for booking integration (run on prod)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.services.google_sheets_service import read_records


def main():
    app = create_app("production")
    with app.app_context():
        sid = app.config["SPREADSHEET_ID"]
        print("SPREADSHEET_ID tail:", (sid or "")[-8:])
        for sheet in ("Clients", "Client_Workouts", "Workouts", "Schedule"):
            try:
                rows = read_records(sid, sheet)
                headers = list(rows[0].keys()) if rows else []
                print(f"\n=== {sheet} ({len(headers)} cols) ===")
                print(headers)
            except Exception as e:
                print(f"\n=== {sheet} ERROR ===", e)


if __name__ == "__main__":
    main()
