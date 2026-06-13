"""Events-3 slug generation and resolution tests."""

from datetime import date

from app.services.events.classifier import classify_competitions_ticker_row
from app.services.events.schema import normalize_competitions_ticker_row
from app.services.events.slug import (
    build_public_slug,
    event_id_tail,
    parse_slug_tail,
    resolve_item_by_slug,
)


def _item(event_id: str, title: str):
    row = {
        "id": event_id,
        "event_name": title,
        "start_date": "2026-09-01",
        "status": "ACTIVE",
        "location": "Test",
    }
    clf = classify_competitions_ticker_row(row)
    return normalize_competitions_ticker_row(row, clf, start_date=date(2026, 9, 1))


class TestSlugGeneration:
    def test_event_id_tail_stable(self):
        assert event_id_tail("comp-published-001") == event_id_tail("comp-published-001")
        assert event_id_tail("comp-published-001").endswith("001") or len(event_id_tail("comp-published-001")) <= 8

    def test_build_public_slug_includes_tail(self):
        item = _item("comp-published-001", "IWWF Open Moscow")
        slug = build_public_slug(item)
        tail = event_id_tail(item.event_id)
        assert slug.endswith(f"-{tail}")

    def test_slug_collision_protected_by_tail(self):
        a = _item("comp-aaa-111", "Championship Alpha")
        b = _item("comp-bbb-222", "Championship Beta")
        assert build_public_slug(a) != build_public_slug(b)

    def test_parse_slug_tail(self):
        item = _item("comp-published-001", "IWWF Open")
        slug = build_public_slug(item)
        assert parse_slug_tail(slug) == event_id_tail(item.event_id)


class TestSlugResolve:
    def test_resolve_by_event_id_tail(self):
        item = _item("comp-published-001", "IWWF Open Moscow")
        slug = build_public_slug(item)
        result = resolve_item_by_slug(slug, [item])
        assert result is not None
        assert result.item.event_id == item.event_id

    def test_title_mismatch_triggers_redirect(self):
        item = _item("comp-published-001", "New Title Here")
        old_slug = "old-title-" + event_id_tail(item.event_id)
        result = resolve_item_by_slug(old_slug, [item])
        assert result is not None
        assert result.redirect_required is True
        assert result.canonical_slug == build_public_slug(item)

    def test_needs_review_not_resolved(self):
        row = {"id": "x1", "raw_title": "Турнир", "location": "X"}
        from app.services.events.classifier import classify_row
        from app.services.events.schema import normalize_raw_feed_row

        clf = classify_row(row)
        item = normalize_raw_feed_row(row, clf)
        slug = build_public_slug(item)
        assert resolve_item_by_slug(slug, [item]) is None
