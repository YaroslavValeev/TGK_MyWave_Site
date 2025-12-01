"""Adapter module for analytics logging.

Этот модуль служит совместимостью: раньше код импортировал
`app.services.google_sheets_analytics.log_analytics_event`, а
реализация находится в `google_sheets_service.py`. Экспортируем
функцию отсюда чтобы не ломать импорты.
"""
from app.services.google_sheets_service import log_analytics_event

__all__ = ["log_analytics_event"]
