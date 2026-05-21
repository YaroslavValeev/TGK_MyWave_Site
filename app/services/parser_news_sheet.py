"""
Адаптер для чтения данных из PARSER_TAB (таблица MyWave_Parser_News).
Поддерживает два варианта:
- PARSER_TAB как Spreadsheet ID отдельной таблицы
- PARSER_TAB как название листа внутри основного SPREADSHEET_ID
"""
import os
import re
from typing import Dict, List, Tuple

from flask import current_app

from app.services.google import read_sheet
from app.modules.logger import get_logger

logger = get_logger(__name__)

DEFAULT_WORKSHEET_TITLE = "raw_feed"

_SPREADSHEET_ID_RE = re.compile(r"^[a-zA-Z0-9-_]{25,}$")


def _looks_like_spreadsheet_id(value: str) -> bool:
    """Проверяет, похоже ли значение на Spreadsheet ID."""
    if not value:
        return False
    return bool(_SPREADSHEET_ID_RE.match(value))


def _parser_sheet_name() -> str:
    return (
        (current_app.config.get("PARSER_SHEET_NAME") if current_app else None)
        or os.getenv("PARSER_SHEET_NAME")
        or DEFAULT_WORKSHEET_TITLE
    ).strip()


def _parser_news_spreadsheet_id() -> str:
    return (
        (current_app.config.get("PARSER_NEWS_SPREADSHEET_ID") if current_app else None)
        or os.getenv("PARSER_NEWS_SPREADSHEET_ID")
        or ""
    ).strip()


def resolve_parser_source() -> Tuple[str, str]:
    """
    Возвращает (spreadsheet_id, worksheet_title) для блога / Parser News.

    Приоритет:
    1. PARSER_NEWS_SPREADSHEET_ID — отдельная таблица Parser News (рекомендуется на prod)
    2. PARSER_TAB как Spreadsheet ID
    3. PARSER_TAB / PARSER_SHEET_NAME как лист внутри SPREADSHEET_ID (Admin/Tg Bot)
    """
    parser_sheet_name = _parser_sheet_name()
    parser_news_id = _parser_news_spreadsheet_id()
    if _looks_like_spreadsheet_id(parser_news_id):
        return parser_news_id, parser_sheet_name

    parser_tab = (os.getenv("PARSER_TAB") or "").strip()
    main_spreadsheet_id = current_app.config.get("SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID") or ""

    if _looks_like_spreadsheet_id(parser_tab):
        return parser_tab, parser_sheet_name

    if not main_spreadsheet_id:
        raise RuntimeError(
            "SPREADSHEET_ID is empty and PARSER_NEWS_SPREADSHEET_ID / PARSER_TAB not set"
        )

    worksheet_title = parser_tab or parser_sheet_name
    return main_spreadsheet_id, worksheet_title


def fetch_parser_news_rows() -> Tuple[List[Dict], List[str]]:
    """
    Читает строки из PARSER_TAB (raw_feed или news_articles).
    Возвращает (records, headers).
    """
    spreadsheet_id, worksheet_title = resolve_parser_source()
    logger.info(f"[parser_news_sheet] Чтение из spreadsheet_id={spreadsheet_id[:20]}..., worksheet={worksheet_title}")
    records, headers = read_sheet(spreadsheet_id, worksheet_title)
    logger.info(f"[parser_news_sheet] Прочитано {len(records)} строк, заголовков: {len(headers)}")
    return records, headers
