"""Unit tests for Tour Camp showcase (/camps) service layer."""

from datetime import date
from unittest.mock import patch

import pytest

from app.services.camps.showcase import (
    fetch_showcase_camps,
    fetch_showcase_detail,
    is_showcase_public,
    to_showcase_view,
)
from app.services.camps.tour_client import TourCampFetchError


TODAY = date(2026, 7, 21)

MVP_CAMP = {
    "id": "tour_real_wakesurf_partner_v1",
    "title": "Partner Wakesurf Camp",
    "publication_status": "published",
    "content_rights_status": "unknown",
    "sport": "wakesurf",
    "country": "Россия",
    "city": "Москва",
    "start_date": "2026-08-01",
    "end_date": "2026-08-08",
    "duration_days": 8,
    "price_from": 90000,
    "currency": "RUB",
    "availability_status": "available",
    "cover_image_url": "https://cdn.example/cover.jpg",
    "description": "Описание кемпа",
    "organizer_name": "MyWaveTour Partner",
    "included": "Проживание",
    "not_included": "Перелёт",
    "program": ["День 1", "День 2"],
    "booking_url": "https://booking.example/camp",
    "source_url": "https://mywavetour.ru/camp/partner",
}

SYNTHETIC_CAMP = {
    **MVP_CAMP,
    "id": "tour_camp_api_mvp_wakesurf_v1",
    "title": "Пилотный вейксерф-кемп MyWave Tour",
    "source_url": "https://mywavetour.ru/program/camp_api_mvp_wakesurf_v1",
}


def test_is_showcase_public_filters_hidden_and_restricted():
    assert is_showcase_public(MVP_CAMP, today=TODAY) is True
    assert is_showcase_public({**MVP_CAMP, "publication_status": "hidden"}, today=TODAY) is False
    assert is_showcase_public({**MVP_CAMP, "publication_status": "archived"}, today=TODAY) is False
    assert is_showcase_public({**MVP_CAMP, "content_rights_status": "restricted"}, today=TODAY) is False


def test_is_showcase_public_filters_non_ru_audience_and_other_sports():
    assert is_showcase_public({**MVP_CAMP, "audience_language": ["ru"]}, today=TODAY) is True
    assert is_showcase_public({**MVP_CAMP, "audience_language": ["en"]}, today=TODAY) is False
    assert is_showcase_public({**MVP_CAMP, "sport": ["wakesurf"]}, today=TODAY) is True
    assert is_showcase_public({**MVP_CAMP, "sport": ["ski"]}, today=TODAY) is False


def test_is_showcase_public_filters_past_camps_keeps_current_and_upcoming():
    past = {**MVP_CAMP, "start_date": "2026-05-09", "end_date": "2026-05-17"}
    current = {**MVP_CAMP, "start_date": "2026-07-18", "end_date": "2026-07-25"}
    upcoming = {**MVP_CAMP, "start_date": "2026-08-31", "end_date": "2026-09-06"}
    ended_yesterday = {**MVP_CAMP, "start_date": "2026-07-10", "end_date": "2026-07-20"}
    assert is_showcase_public(past, today=TODAY) is False
    assert is_showcase_public(ended_yesterday, today=TODAY) is False
    assert is_showcase_public(current, today=TODAY) is True
    assert is_showcase_public(upcoming, today=TODAY) is True
    assert is_showcase_public({**MVP_CAMP, "start_date": None, "end_date": None}, today=TODAY) is True


def test_is_showcase_public_filters_synthetic_and_test_camps():
    assert is_showcase_public(SYNTHETIC_CAMP, today=TODAY) is False
    assert is_showcase_public({**MVP_CAMP, "id": "tour_demo_camp_1", "title": "Real title"}, today=TODAY) is False
    assert is_showcase_public({**MVP_CAMP, "title": "Тестовый кемп для smoke"}, today=TODAY) is False
    assert is_showcase_public(MVP_CAMP, today=TODAY) is True


def test_to_showcase_view_unknown_rights_not_confirmed_partnership():
    view = to_showcase_view(MVP_CAMP)
    assert view["id"] == "tour_real_wakesurf_partner_v1"
    assert view["partnership_confirmed"] is False
    assert view["source_badge"] == "Из MyWaveTour"
    assert view["content_rights_notice"]
    assert view["price_label"].startswith("от ")
    assert view["availability_label"] == "Есть места"


def test_fetch_showcase_camps_empty_is_not_error():
    with patch("app.services.camps.showcase.fetch_tour_camps", return_value=[]):
        result = fetch_showcase_camps()
    assert result.state == "empty"
    assert result.camps == []


def test_fetch_showcase_camps_auth_error():
    with patch(
        "app.services.camps.showcase.fetch_tour_camps",
        side_effect=TourCampFetchError(401, "auth", kind="auth"),
    ):
        result = fetch_showcase_camps()
    assert result.state == "error_auth"
    assert result.camps == []


def test_fetch_showcase_camps_server_error():
    with patch(
        "app.services.camps.showcase.fetch_tour_camps",
        side_effect=TourCampFetchError(503, "server", kind="server"),
    ):
        result = fetch_showcase_camps()
    assert result.state == "error_server"


def test_fetch_showcase_detail_ok():
    with patch("app.services.camps.showcase.fetch_tour_camp_detail", return_value=MVP_CAMP):
        result = fetch_showcase_detail(MVP_CAMP["id"])
    assert result.state == "ok"
    assert result.camp["title"] == "Partner Wakesurf Camp"


def test_fetch_showcase_detail_hides_synthetic_camp():
    with patch("app.services.camps.showcase.fetch_tour_camp_detail", return_value=SYNTHETIC_CAMP):
        result = fetch_showcase_detail(SYNTHETIC_CAMP["id"])
    assert result.state == "not_found"


def test_fetch_showcase_detail_not_found():
    with patch(
        "app.services.camps.showcase.fetch_tour_camp_detail",
        side_effect=TourCampFetchError(404, "missing", kind="client"),
    ):
        result = fetch_showcase_detail("missing")
    assert result.state == "not_found"


def test_fetch_showcase_detail_falls_back_to_list_on_404(caplog):
    with patch(
        "app.services.camps.showcase.fetch_tour_camp_detail",
        side_effect=TourCampFetchError(404, "missing", kind="client"),
    ), patch(
        "app.services.camps.showcase.fetch_tour_camps",
        return_value=[MVP_CAMP],
    ):
        with caplog.at_level("WARNING"):
            result = fetch_showcase_detail(MVP_CAMP["id"])
    assert result.state == "ok"
    assert result.camp["id"] == MVP_CAMP["id"]
    assert any("camp_detail_fallback_list" in r.message for r in caplog.records)
