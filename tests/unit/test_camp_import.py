"""Unit tests for Camp import normalization, validation, and Tour client."""

from datetime import date

from app.services.camps.normalize import normalize_tour_camp, normalized_title_key
from app.services.camps.tour_client import TourCampFetchError, parse_feed_payload
from app.services.camps.validate import validate_camp


def test_normalize_tour_camp_basic():
    raw = {
        "id": "tour-42",
        "title": "Вейксерф кемп в Сочи",
        "discipline": "вейксерф",
        "start_date": "2026-08-10",
        "end_date": "2026-08-17",
        "country": "Россия",
        "city": "Сочи",
        "price": 85000,
        "url": "https://www.mywavetour.ru/camp/sochi",
    }
    camp = normalize_tour_camp(raw)
    assert camp["source_system"] == "mywavetour"
    assert camp["external_id"] == "tour-42"
    assert camp["sport"] == "wakesurf"
    assert camp["start_date"] == date(2026, 8, 10)
    assert camp["price_from"] == 85000
    assert camp["slug"]


def test_normalize_tour_camp_sport_array_and_tour_prefix():
    raw = {
        "id": "99",
        "title": "Mixed camp",
        "sport": ["wakesurf", "wakeboard"],
        "start_date": "2026-09-01",
    }
    camp = normalize_tour_camp(raw)
    assert camp["external_id"] == "tour_99"
    assert camp["sport"] == "mixed"


def test_validate_camp_requires_title_and_slug():
    ok, errs = validate_camp({"source_system": "mywavetour", "sport": "wakesurf", "level": "all_levels"})
    assert not ok
    assert "title_required" in errs
    assert "slug_required" in errs


def test_normalized_title_key_collapses_spaces():
    assert normalized_title_key("  Вейк   Кемп  ") == normalized_title_key("вейк кемп")


def test_parse_feed_variant_b_array():
    items, next_offset = parse_feed_payload([{"id": "tour_1", "title": "A"}])
    assert len(items) == 1
    assert next_offset is None


def test_parse_feed_variant_a_items_next_offset():
    items, next_offset = parse_feed_payload({"items": [{"id": "tour_2"}], "next_offset": 100})
    assert len(items) == 1
    assert next_offset == 100


def test_tour_camp_fetch_error_attrs():
    err = TourCampFetchError(403, "forbidden")
    assert err.status_code == 403
    assert "forbidden" in str(err)
