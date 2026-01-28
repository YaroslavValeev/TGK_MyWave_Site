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


def resolve_parser_source() -> Tuple[str, str]:
    """
    Возвращает (spreadsheet_id, worksheet_title) для PARSER_TAB.

    Логика:
    - если PARSER_TAB похож на Spreadsheet ID -> используем его как spreadsheet_id,
      а лист берём по умолчанию DEFAULT_WORKSHEET_TITLE (или из PARSER_SHEET_NAME)
    - иначе считаем PARSER_TAB названием листа внутри основного SPREADSHEET_ID
    """
    parser_tab = (os.getenv("PARSER_TAB") or "").strip()
    parser_sheet_name = (os.getenv("PARSER_SHEET_NAME") or DEFAULT_WORKSHEET_TITLE).strip()
    main_spreadsheet_id = current_app.config.get("SPREADSHEET_ID") or os.getenv("SPREADSHEET_ID") or ""

    if _looks_like_spreadsheet_id(parser_tab):
        return parser_tab, parser_sheet_name

    if not main_spreadsheet_id:
        raise RuntimeError("SPREADSHEET_ID is empty, cannot resolve PARSER_TAB as worksheet name")

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
