"""Unit-тесты: competitions ticker visibility, текст, API."""
from datetime import date, timedelta

from app.services.competitions.visibility import (
    build_ticker_text,
    is_ticker_live_row,
    is_ticker_visible_row,
    normalize_url,
    parse_iso_date,
    resolve_ticker_href,
)


def _row(**kwargs):
    base = {
        "status": "ACTIVE",
        "discipline": "wakesurf",
        "event_name": "Test Cup",
        "location": "Orlando",
        "country": "USA",
        "start_date": "2026-08-01",
        "end_date": "2026-08-03",
        "event_url": "https://example.com/event",
        "source_url": "https://example.com/source",
    }
    base.update(kwargs)
    return base


def test_parse_iso_date_formats():
    assert parse_iso_date("2026-06-15") == date(2026, 6, 15)
    assert parse_iso_date("15.06.2026") == date(2026, 6, 15)


def test_visible_active_future_end():
    today = date(2026, 5, 19)
    assert is_ticker_visible_row(_row(), today=today) is True


def test_hidden_archived():
    today = date(2026, 5, 19)
    assert is_ticker_visible_row(_row(status="ARCHIVED"), today=today) is False


def test_hidden_past_end_date():
    today = date(2026, 5, 19)
    assert is_ticker_visible_row(
        _row(start_date="2026-01-01", end_date="2026-01-05"),
        today=today,
    ) is False


def test_hidden_draft():
    today = date(2026, 5, 19)
    assert is_ticker_visible_row(_row(status="DRAFT"), today=today) is False


def test_hidden_missing_event_name():
    today = date(2026, 5, 19)
    assert is_ticker_visible_row(_row(event_name=""), today=today) is False


def test_resolve_href_prefers_source_url():
    row = _row(event_url="https://event.example", source_url="https://source.example")
    assert resolve_ticker_href(row) == "https://source.example"


def test_resolve_href_fallback_event_url():
    row = _row(event_url="example.com/event", source_url="")
    assert resolve_ticker_href(row) == "https://example.com/event"


def test_resolve_href_fallback_source_url():
    row = _row(event_url="", source_url="example.com/page")
    assert resolve_ticker_href(row) == "https://example.com/page"


def test_normalize_url_rejects_garbage():
    assert normalize_url("-") is None
    assert normalize_url("") is None


def test_build_ticker_text_custom():
    row = _row(ticker_text="Custom marquee line")
    assert build_ticker_text(row) == "Custom marquee line"


def test_build_ticker_text_auto():
    row = _row(ticker_text="")
    text = build_ticker_text(row)
    assert "Test Cup" in text
    assert "Orlando" in text
    assert "Wakesurf" in text


def test_api_competitions_ticker_route(client, mocker):
    fake = [
        {
            "id": "e1",
            "label": "Wakesurf · Cup · Orlando, USA · 01.08–03.08.2026",
            "href": "https://example.com",
            "discipline": "wakesurf",
            "event_name": "Cup",
            "start_date": "2026-08-01",
            "end_date": "2026-08-03",
            "source_name": "IWWF",
        }
    ]
    mocker.patch(
        "app.routes.competitions.get_ticker_items",
        return_value=fake,
    )
    rv = client.get("/api/competitions/ticker")
    assert rv.status_code == 200
    data = rv.get_json()
    assert data["count"] == 1
    assert data["items"][0]["label"] == fake[0]["label"]
    assert "spreadsheet_id_tail" in data


def test_home_shows_ticker_when_items(client, mocker):
    fake = [
        {
            "id": "e1",
            "label": "Future Event Test",
            "href": "https://example.com",
        }
    ]
    mocker.patch(
        "app.services.competitions.store.get_ticker_items",
        return_value=fake,
    )
    mocker.patch(
        "app.services.blog.store.get_posts",
        return_value=([], 0),
    )
    rv = client.get("/")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert "home-competitions-ticker" in html
    assert "Future Event Test" in html


def test_home_hides_ticker_when_empty(client, mocker):
    mocker.patch(
        "app.services.competitions.store.get_ticker_items",
        return_value=[],
    )
    mocker.patch(
        "app.services.blog.store.get_posts",
        return_value=([], 0),
    )
    rv = client.get("/")
    html = rv.get_data(as_text=True)
    assert "home-competitions-ticker" not in html


def test_ongoing_event_visible_if_end_today():
    today = date.today()
    start = (today - timedelta(days=2)).isoformat()
    end = today.isoformat()
    assert is_ticker_visible_row(
        _row(start_date=start, end_date=end),
        today=today,
    ) is True


def test_live_row_when_event_in_progress():
    today = date(2026, 6, 18)
    row = _row(start_date="2026-06-17", end_date="2026-06-19")
    assert is_ticker_live_row(row, today=today) is True


def test_live_row_false_before_start():
    today = date(2026, 6, 10)
    row = _row(start_date="2026-06-17", end_date="2026-06-19")
    assert is_ticker_live_row(row, today=today) is False


def test_home_ticker_marks_live_item(client, mocker):
    today = date(2026, 6, 18)
    fake = [
        {
            "id": "e-live",
            "label": "Live Event Now",
            "href": "https://example.com",
            "is_live": True,
        }
    ]
    mocker.patch(
        "app.services.competitions.store.get_ticker_items",
        return_value=fake,
    )
    mocker.patch(
        "app.services.blog.store.get_posts",
        return_value=([], 0),
    )
    html = client.get("/").get_data(as_text=True)
    assert "home-competitions-ticker__item--live" in html
    assert "Live Event Now" in html
