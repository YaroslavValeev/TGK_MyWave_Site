# app/services/site_analytics.py
from __future__ import annotations

from typing import Any, Dict
import logging

from flask import current_app

from app.services.google_sheets_analytics import log_analytics_event

logger = logging.getLogger(__name__)


def log_site_booking_event(
    booking_data: Dict[str, Any],
    ip: str = "",
    user_agent: str = "",
) -> bool:
    """
    Логирует событие бронирования с сайта в Google Sheets
    через универсальный логгер log_analytics_event.

    booking_data — словарь с ключами:
      - date, time, name, phone
      - client_id, workout_id (если есть)
      - service_type (boat/gym), source (site/bot/...), booking_type (client/admin/...)
    """
    try:
        # Фича-флаг: можно глобально выключить аналитику
        if not current_app.config.get("ENABLE_ANALYTICS", True):
            return False

        # Отдельная таблица под аналитику, если указана
        sheet_id = current_app.config.get("ANALYTICS_SHEET_SPREADSHEET_ID") or None
        sheet_name = current_app.config.get("ANALYTICS_SHEET_NAME") or None

        # Стандартизированный payload для log_analytics_event
        payload: Dict[str, Any] = {
            "event": "booking_created",
            "context": "site_booking",
            "user_key": booking_data.get("client_id")
            or booking_data.get("phone", ""),
            "rule_id": booking_data.get("service_type", ""),
            "item_id": booking_data.get("workout_id", ""),
            "type": booking_data.get("source", "site"),
            "meta": booking_data,
            "ip": ip or "",
            "user_agent": user_agent or "",
        }

        return log_analytics_event(
            payload,
            spreadsheet_id=sheet_id,
            worksheet_name=sheet_name,
        )
    except Exception as e:
        logger.error("Failed to log site booking event: %s", e)
        return False
