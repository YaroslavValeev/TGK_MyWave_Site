from __future__ import annotations

from typing import Dict, Any
from datetime import datetime, timezone
import logging

from flask import current_app

from app.services.google_sheets_analytics import read_records

logger = logging.getLogger(__name__)


def get_sponsor_kpi(project: str) -> Dict[str, Any]:
    """
    Базовые KPI для спонсоров по проекту: 'safari' или 'challenge'.
    Каркас без привязки к конкретной схеме событий.
    """
    try:
        sheet_id = current_app.config.get("ANALYTICS_SHEET_SPREADSHEET_ID")
        sheet_name = current_app.config.get(
            "ANALYTICS_SHEET_NAME", "analytics_statistics"
        )
        events: list[dict] = []
        if sheet_id:
            try:
                events = read_records(sheet_id, sheet_name)
            except Exception:
                events = []

        total_events = len(events)
        return {
            "project": project,
            "total_events": total_events,
            "impressions": 0,
            "participants": 0,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        logger.error("get_sponsor_kpi error: %s", e)
        return {
            "project": project,
            "error": "kpi_error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
