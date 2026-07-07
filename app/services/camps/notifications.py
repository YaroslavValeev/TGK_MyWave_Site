"""Telegram notifications for Camp leads."""

from __future__ import annotations

from typing import Any, Dict

from app.database.camp_models import Camp
from app.services.camps.public import get_effective_camp
from app.services.notifications import send_telegram_notification


def format_camp_lead_message(camp: Camp, payload: Dict[str, Any]) -> str:
    eff = get_effective_camp(camp)
    dates = ""
    if eff.get("start_date"):
        dates = eff["start_date"]
        if eff.get("end_date") and eff["end_date"] != eff["start_date"]:
            dates = f"{eff['start_date']} — {eff['end_date']}"
    lines = [
        "Новая заявка на Camp",
        "",
        f"Кемп: {eff.get('title')}",
        f"Даты: {dates or '—'}",
        f"Страна: {eff.get('country') or '—'}",
        f"Имя: {payload.get('name') or '—'}",
        f"Телефон: {payload.get('phone') or '—'}",
        f"Telegram: {payload.get('telegram') or '—'}",
        f"Уровень: {payload.get('level') or '—'}",
        f"Комментарий: {payload.get('comment') or '—'}",
        "Источник: Site / Camp",
    ]
    return "\n".join(lines)


def notify_camp_lead(camp: Camp, payload: Dict[str, Any]) -> bool:
    text = format_camp_lead_message(camp, payload)
    return bool(send_telegram_notification(text))
