"""Источник данных: лист competitions_ticker в таблице Parser News."""
import os
from typing import Tuple

from flask import current_app

from app.services.parser_news_sheet import (
    _looks_like_spreadsheet_id,
    _parser_news_spreadsheet_id,
)

DEFAULT_WORKSHEET_TITLE = "competitions_ticker"


def _competitions_sheet_name() -> str:
    return (
        (current_app.config.get("COMPETITIONS_SHEET_NAME") if current_app else None)
        or os.getenv("COMPETITIONS_SHEET_NAME")
        or DEFAULT_WORKSHEET_TITLE
    ).strip()


def resolve_competitions_source() -> Tuple[str, str]:
    """
    (spreadsheet_id, worksheet_title) — та же таблица, что блог (PARSER_NEWS_SPREADSHEET_ID).
    """
    parser_news_id = _parser_news_spreadsheet_id()
    if _looks_like_spreadsheet_id(parser_news_id):
        return parser_news_id, _competitions_sheet_name()

    parser_tab = (os.getenv("PARSER_TAB") or "").strip()
    main_spreadsheet_id = (
        current_app.config.get("SPREADSHEET_ID") if current_app else None
    ) or os.getenv("SPREADSHEET_ID") or ""

    if _looks_like_spreadsheet_id(parser_tab):
        return parser_tab, _competitions_sheet_name()

    if not main_spreadsheet_id:
        raise RuntimeError(
            "PARSER_NEWS_SPREADSHEET_ID is empty and PARSER_TAB not set for competitions ticker"
        )

    worksheet_title = parser_tab or _competitions_sheet_name()
    return main_spreadsheet_id, worksheet_title
