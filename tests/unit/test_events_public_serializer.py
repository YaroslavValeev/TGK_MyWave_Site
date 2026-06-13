"""Events-3 public serializer safety tests."""

from datetime import date

from app.services.events.classifier import classify_competitions_ticker_row
from app.services.events.public_serializer import (
    assert_public_payload_safe,
    build_public_json_ld_item,
    serialize_public_card,
    serialize_public_detail,
)
from app.services.events.schema import normalize_competitions_ticker_row


def _published_item():
    row = {
        "id": "t-pub-001",
        "event_name": "IWWF Open",
        "start_date": "2026-09-01",
        "status": "ACTIVE",
        "location": "Orlando",
        "source_url": "https://secret.example/event",
        "raw_content": "secret body",
    }
    clf = classify_competitions_ticker_row(row)
    return normalize_competitions_ticker_row(row, clf, start_date=date(2026, 9, 1))


class TestPublicSerializer:
    def test_card_safe(self):
        payload = serialize_public_card(_published_item())
        assert_public_payload_safe(payload)
        assert "source_url" not in payload
        assert "raw_content" not in payload

    def test_detail_safe(self):
        payload = serialize_public_detail(_published_item())
        assert_public_payload_safe(payload)

    def test_json_ld_uses_mywavewake_domain(self, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        item = _published_item()
        ld = build_public_json_ld_item(item)
        assert ld["url"].startswith("https://mywavewake.ru/")
