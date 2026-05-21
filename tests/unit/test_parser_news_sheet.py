"""Тесты resolve_parser_source — приоритет PARSER_NEWS_SPREADSHEET_ID."""
import os

import pytest

from app.services import parser_news_sheet as pns

PARSER_NEWS_ID = "1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50"
ADMIN_BOT_ID = "1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0"


@pytest.fixture(autouse=True)
def _clear_parser_env(monkeypatch):
    for key in (
        "PARSER_NEWS_SPREADSHEET_ID",
        "PARSER_TAB",
        "PARSER_SHEET_NAME",
        "SPREADSHEET_ID",
    ):
        monkeypatch.delenv(key, raising=False)


def test_resolve_prefers_parser_news_spreadsheet_id(app, monkeypatch):
    monkeypatch.setenv("PARSER_NEWS_SPREADSHEET_ID", PARSER_NEWS_ID)
    monkeypatch.setenv("SPREADSHEET_ID", ADMIN_BOT_ID)
    monkeypatch.setenv("PARSER_TAB", "raw_feed")

    with app.app_context():
        app.config["PARSER_NEWS_SPREADSHEET_ID"] = PARSER_NEWS_ID
        app.config["SPREADSHEET_ID"] = ADMIN_BOT_ID
        sid, sheet = pns.resolve_parser_source()

    assert sid == PARSER_NEWS_ID
    assert sheet == "raw_feed"


def test_resolve_parser_tab_as_spreadsheet_id(app, monkeypatch):
    monkeypatch.setenv("PARSER_TAB", PARSER_NEWS_ID)
    monkeypatch.setenv("SPREADSHEET_ID", ADMIN_BOT_ID)

    with app.app_context():
        sid, sheet = pns.resolve_parser_source()

    assert sid == PARSER_NEWS_ID
    assert sheet == "raw_feed"


def test_resolve_worksheet_in_main_spreadsheet(app, monkeypatch):
    monkeypatch.setenv("SPREADSHEET_ID", ADMIN_BOT_ID)
    monkeypatch.setenv("PARSER_TAB", "raw_feed")
    monkeypatch.delenv("PARSER_NEWS_SPREADSHEET_ID", raising=False)

    with app.app_context():
        app.config["PARSER_NEWS_SPREADSHEET_ID"] = ""
        app.config["SPREADSHEET_ID"] = ADMIN_BOT_ID
        sid, sheet = pns.resolve_parser_source()

    assert sid == ADMIN_BOT_ID
    assert sheet == "raw_feed"
