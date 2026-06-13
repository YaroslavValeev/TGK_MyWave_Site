"""Events-2 loader tests."""

from app.services.events.loader import (
    load_classified_items,
    load_from_competitions_ticker,
    load_from_raw_feed,
)


def _raw_rows():
    return [
        {
            "id": "n1",
            "title": "Новости клуба",
            "status": "PUBLISHED",
            "text": "body",
        },
        {
            "id": "c1",
            "raw_title": "Чемпионат России",
            "start_date": "2026-08-01",
            "location": "Москва",
        },
    ]


def _ticker_rows():
    return [
        {
            "id": "t1",
            "status": "ACTIVE",
            "event_name": "IWWF Open",
            "start_date": "2026-09-01",
            "end_date": "2026-09-03",
            "location": "Orlando",
        }
    ]


class TestEventsLoader:
    def test_load_from_raw_feed_classifies(self):
        items = load_from_raw_feed(_raw_rows())
        by_id = {it.event_id: it for it in items}
        assert by_id["n1"].content_type == "news"
        assert by_id["c1"].content_type == "competition"

    def test_load_from_ticker(self):
        items = load_from_competitions_ticker(_ticker_rows())
        assert len(items) == 1
        assert items[0].content_type == "competition"
        assert items[0].title == "IWWF Open"

    def test_load_classified_items_injected(self):
        def raw_loader():
            return _raw_rows(), []

        def ticker_loader():
            return _ticker_rows(), []

        all_items = load_classified_items(
            source="all",
            raw_feed_loader=raw_loader,
            ticker_loader=ticker_loader,
        )
        assert len(all_items) == 3

        raw_only = load_classified_items(source="raw_feed", raw_feed_loader=raw_loader)
        assert len(raw_only) == 2
