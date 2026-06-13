"""Events-2 API tests."""

from app.services.events.loader import load_classified_items
from app.services.events.serializer import assert_api_payload_safe, serialize_api_item
from app.services.events.store import invalidate_events_cache, list_review_queue


def _fixture_loader(**_kwargs):
    return load_classified_items(
        source="all",
        raw_feed_loader=lambda: (
            [
                {
                    "id": "n1",
                    "title": "Новости",
                    "status": "PUBLISHED",
                    "text": "x",
                },
                {
                    "id": "c1",
                    "raw_title": "Турнир",
                    "start_date": "2026-08-01",
                    "location": "Москва",
                },
                {
                    "id": "c2",
                    "raw_title": "Турнир без даты",
                    "location": "Санкт-Петербург",
                },
            ],
            [],
        ),
        ticker_loader=lambda: ([], []),
    )


class TestEventsApiFlagsOff:
    def test_events_list_disabled(self, client):
        rv = client.get("/api/events")
        assert rv.status_code == 503
        assert rv.get_json().get("error") == "events_api_disabled"

    def test_diagnostics_disabled(self, client):
        rv = client.get("/api/events/diagnostics")
        assert rv.status_code == 503

    def test_review_queue_disabled(self, client):
        rv = client.get("/api/events/review-queue")
        assert rv.status_code == 503


class TestEventsApiEnabled:
    def test_events_list_ok(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _fixture_loader,
        )
        rv = client.get("/api/events?content_type=competition")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["count"] == 2
        assert data["items"][0]["content_type"] == "competition"
        for item in data["items"]:
            assert_api_payload_safe(item)
            assert "source_url" not in item
            assert "short_description" not in item

    def test_review_queue_ok(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_REVIEW_API_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _fixture_loader,
        )
        rv = client.get("/api/events/review-queue")
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["filters_applied"]["track_status"] == "needs_review"
        assert data["total"] >= 1
        assert all(it["needs_review"] for it in data["items"])

    def test_diagnostics_ok(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _fixture_loader,
        )
        rv = client.get("/api/events/diagnostics")
        assert rv.status_code == 200
        data = rv.get_json()
        assert "needs_review_count" in data
        assert "spreadsheet_id_tail" in data
        assert "flags" in data


class TestSerializer:
    def test_serialize_api_item_safe(self):
        items = _fixture_loader()
        payload = serialize_api_item(items[0])
        assert_api_payload_safe(payload)
        assert "title" in payload

    def test_review_queue_helper(self):
        invalidate_events_cache()
        result = list_review_queue(loader=_fixture_loader)
        assert result["total"] >= 1
