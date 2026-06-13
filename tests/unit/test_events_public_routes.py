"""Events-3 public route tests."""

from datetime import date

from app.services.events.loader import load_classified_items
from app.services.events.store import invalidate_events_cache
from app.services.events.ticker_links import enrich_competitions_ticker


def _published_rows():
    return [
        {
            "id": "comp-published-001",
            "event_name": "IWWF Open Moscow",
            "start_date": "2026-09-01",
            "end_date": "2026-09-03",
            "location": "Moscow",
            "status": "ACTIVE",
        },
        {
            "id": "c-review",
            "raw_title": "Турнир без даты",
            "location": "СПб",
        },
    ]


def _published_loader(**_kwargs):
    return load_classified_items(
        source="all",
        raw_feed_loader=lambda: (
            [_published_rows()[1]],
            [],
        ),
        ticker_loader=lambda: ([_published_rows()[0]], []),
    )


class TestEventsPublicFlagsOff:
    def test_events_yaml_unchanged(self, client):
        rv = client.get("/events")
        assert rv.status_code == 200
        assert b"events-section" in rv.data
        assert b"event-card" in rv.data or b"no-events-modal" in rv.data

    def test_detail_404_when_flag_off(self, client):
        rv = client.get("/events/some-slug-001")
        assert rv.status_code == 404

    def test_competitions_404_when_flag_off(self, client):
        rv = client.get("/competitions")
        assert rv.status_code == 404

    def test_sitemap_renders_without_jinja_error(self, client):
        rv = client.get("/sitemap.xml")
        assert rv.status_code == 200
        assert b"<urlset" in rv.data
        assert b"</urlset>" in rv.data


class TestEventsPublicFlagsOn:
    def test_events_list_from_store(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        rv = client.get("/events")
        assert rv.status_code == 200
        assert "IWWF Open Moscow".encode() in rv.data
        assert "Турнир без даты".encode("utf-8") not in rv.data

    def test_needs_review_not_in_list(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        rv = client.get("/events")
        assert "Турнир без даты".encode("utf-8") not in rv.data

    def test_needs_review_detail_404(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        rv = client.get("/events/tournament-review-c-review")
        assert rv.status_code == 404

    def test_detail_published_ok(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        from app.services.events.slug import build_public_slug
        from app.services.events.store import get_public_items

        item = get_public_items(loader=_published_loader)[0]
        slug = build_public_slug(item)
        rv = client.get(f"/events/{slug}")
        assert rv.status_code == 200
        assert "IWWF Open Moscow".encode() in rv.data
        assert b"source_url" not in rv.data

    def test_slug_mismatch_redirect(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        from app.services.events.slug import event_id_tail

        tail = event_id_tail("comp-published-001")
        rv = client.get(f"/events/old-name-{tail}")
        assert rv.status_code == 301

    def test_competitions_redirect_302(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        rv = client.get("/competitions", follow_redirects=False)
        assert rv.status_code == 302
        assert "type=competition" in rv.headers.get("Location", "")

    def test_public_ui_on_api_off_no_500(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "0")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        rv = client.get("/events")
        assert rv.status_code == 200

    def test_detail_api_off_503(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "0")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        rv = client.get("/events/any-slug-001")
        assert rv.status_code == 503

    def test_empty_store_yaml_fallback(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            lambda **_: [],
        )
        rv = client.get("/events")
        assert rv.status_code == 200

    def test_load_error_fallback(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()

        def _boom(**_):
            raise RuntimeError("sheets down")

        monkeypatch.setattr("app.services.events.store.load_classified_items", _boom)
        rv = client.get("/events")
        assert rv.status_code == 200

    def test_mobile_filters_markup(self, client, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        rv = client.get("/events")
        assert b"events-filters" in rv.data
        assert b"<details" in rv.data


class TestTickerLinks:
    def test_enrich_internal_link_for_public_item(self, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        items = enrich_competitions_ticker(
            [{"id": "comp-published-001", "label": "IWWF", "href": "https://ext.example"}]
        )
        assert items[0]["href"].startswith("/events/")
        assert items[0]["href_external"] is False

    def test_enrich_keeps_external_when_not_public(self, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "1")
        invalidate_events_cache()
        monkeypatch.setattr(
            "app.services.events.store.load_classified_items",
            _published_loader,
        )
        items = enrich_competitions_ticker(
            [{"id": "unknown-id", "label": "X", "href": "https://ext.example"}]
        )
        assert items[0]["href"] == "https://ext.example"
        assert items[0]["href_external"] is True

    def test_enrich_unchanged_when_flags_off(self, monkeypatch):
        monkeypatch.setenv("EVENTS_PUBLIC_UI_ENABLED", "0")
        raw = [{"id": "1", "label": "X", "href": "https://ext.example"}]
        assert enrich_competitions_ticker(raw) == raw
