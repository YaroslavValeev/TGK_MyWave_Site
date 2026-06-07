#!/usr/bin/env python3
"""S8 — Calendar API evidence dump (Variant B). Run on staging host."""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

STAGING_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(STAGING_DIR, "..", ".."))
for p in (ROOT, STAGING_DIR):
    if p not in sys.path:
        sys.path.insert(0, p)

from _staging_env import load_staging_dotenv

DATE = os.environ.get("S8_DATE", "2026-06-12")
TZ = ZoneInfo("Europe/Moscow")


def main() -> int:
    load_staging_dotenv()
    from app import create_app
    from app.services.google import get_google_services

    day = datetime.strptime(DATE, "%Y-%m-%d").date()
    time_min = datetime.combine(day, datetime.min.time(), tzinfo=TZ).isoformat()
    time_max = datetime.combine(day, datetime.max.time(), tzinfo=TZ).isoformat()

    app = create_app()
    with app.app_context():
        cal_id = app.config["GOOGLE_CALENDAR_ID"]
        sheet_id = app.config.get("SPREADSHEET_ID", "")
        print("s8_calendar_id", cal_id, file=sys.stderr)
        print("s8_spreadsheet_id", sheet_id, file=sys.stderr)
        _, _, cal = get_google_services()
        result = cal.events().list(
            calendarId=cal_id,
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        ).execute(num_retries=2)

        out = []
        for ev in result.get("items", []):
            start = (ev.get("start") or {}).get("dateTime", "")
            end = (ev.get("end") or {}).get("dateTime", "")
            props = (ev.get("extendedProperties") or {}).get("private") or {}
            dur_min = None
            if start and end:
                s = datetime.fromisoformat(start.replace("Z", "+00:00"))
                e = datetime.fromisoformat(end.replace("Z", "+00:00"))
                dur_min = int((e - s).total_seconds() // 60)
            out.append(
                {
                    "id": ev.get("id"),
                    "summary": ev.get("summary"),
                    "location": ev.get("location"),
                    "start": start,
                    "end": end,
                    "duration_min": dur_min,
                    "set_count": props.get("set_count"),
                    "service_type": props.get("service_type"),
                    "booking_id": props.get("booking_id"),
                }
            )

    boat = next((x for x in out if x.get("start") and "T07:00" in x["start"]), None)
    gym = next((x for x in out if x.get("start") and "T16:00" in x["start"]), None)

    checks: list[tuple[str, bool]] = []
    if boat:
        checks.append(("boat_07_duration_90", boat.get("duration_min") == 90))
        checks.append(("boat_07_location_kater", (boat.get("location") or "") == "Катер"))
        checks.append(("boat_07_set_count_3", str(boat.get("set_count")) == "3"))
        summary = boat.get("summary") or ""
        checks.append(("boat_07_summary_v2", "WEB_ID:" in summary and "сет" in summary.lower()))
    else:
        checks.append(("boat_07_found", False))

    if gym:
        checks.append(("gym_16_duration_90", gym.get("duration_min") == 90))
        checks.append(("gym_16_location_zal", (gym.get("location") or "") == "Зал"))
        gsummary = gym.get("summary") or ""
        checks.append(("gym_16_summary_v2", "WEB_ID:" in gsummary and "Зал" in gsummary))
    else:
        checks.append(("gym_16_found", False))

    report = {
        "date": DATE,
        "calendar_id_hint": "from GOOGLE_CALENDAR_ID",
        "event_count": len(out),
        "events": out,
        "s8_checks": [{"name": n, "pass": p} for n, p in checks],
        "s8_pass": all(p for _, p in checks),
    }

    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["s8_pass"]:
        print("S8_ok")
        return 0
    print("S8_partial_or_fail")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
