"""Release S3: client ICS / Google Calendar human titles, LOCATION, duration."""

from __future__ import annotations

from urllib.parse import parse_qs, unquote, urlparse

from app.config.venue import MYWAVE_VENUE
from app.services.booking.client_calendar import (
    build_client_venues_payload,
    build_ics_event,
    client_calendar_duration_minutes,
    client_calendar_summary,
    client_venue_for_service,
    google_calendar_template_url,
)


def test_summary_boat_and_gym_ru_labels():
    assert client_calendar_summary("boat", "Иван Петров") == "Катер MyWave — Иван Петров"
    assert client_calendar_summary("gym", "Анна") == "Зал MyWave — Анна"
    assert "boat" not in client_calendar_summary("boat", "Тест")
    assert "gym" not in client_calendar_summary("gym", "Тест")


def test_summary_empty_name_fallback():
    assert client_calendar_summary("boat", "") == "Катер MyWave — Клиент"
    assert client_calendar_summary("boat", "   ") == "Катер MyWave — Клиент"


def test_duration_boat_sets_1_to_4():
    assert client_calendar_duration_minutes("boat", 1) == 30
    assert client_calendar_duration_minutes("boat", 2) == 60
    assert client_calendar_duration_minutes("boat", 3) == 90
    assert client_calendar_duration_minutes("boat", 4) == 120


def test_duration_gym_and_unknown():
    assert client_calendar_duration_minutes("gym", 99) == 90
    assert client_calendar_duration_minutes("camp") == 120
    assert client_calendar_duration_minutes("other") == 60


def test_venue_boat_location_from_canonical_not_url():
    boat = client_venue_for_service("boat")
    assert boat["location"] == MYWAVE_VENUE["location_label"]
    assert "Старт катания" in boat["location"]
    assert boat["map_url"].startswith("https://yandex.ru/maps")
    assert boat["location"] != boat["map_url"]
    assert "http" not in boat["location"]


def test_venue_gym_location_label():
    gym = client_venue_for_service("gym")
    assert gym["location"] == "Зал MyWave"
    assert "yandex.ru/maps" in gym["map_url"]


def test_venues_payload_keys():
    payload = build_client_venues_payload()
    assert set(payload.keys()) == {"boat", "gym"}


def test_ics_summary_location_dtstart_dtend_boat_two_sets():
    ics = build_ics_event(
        service_type="boat",
        client_name="Иван",
        date="2026-07-20",
        time="10:00",
        set_count=2,
        phone="+79990001122",
        uid="test-uid@mywave",
    )
    assert "SUMMARY:Катер MyWave — Иван" in ics
    assert f"LOCATION:{MYWAVE_VENUE['location_label']}" in ics
    assert "DTSTART:20260720T070000Z" in ics  # 10:00 MSK = 07:00 UTC
    assert "DTEND:20260720T080000Z" in ics  # +60 min
    assert "Запись в MyWave: boat" not in ics
    assert "Услуга: Катер MyWave" in ics


def test_ics_gym_90_minutes():
    ics = build_ics_event(
        service_type="gym",
        client_name="Анна",
        date="2026-07-20",
        time="18:00",
        set_count=1,
        uid="gym-uid@mywave",
    )
    assert "SUMMARY:Зал MyWave — Анна" in ics
    assert "LOCATION:Зал MyWave" in ics
    assert "DTSTART:20260720T150000Z" in ics
    assert "DTEND:20260720T163000Z" in ics


def test_google_calendar_url_text_and_location():
    url = google_calendar_template_url(
        service_type="boat",
        client_name="Иван",
        date="2026-07-20",
        time="10:00",
        set_count=1,
        phone="+7999",
    )
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert unquote(qs["text"][0]) == "Катер MyWave — Иван"
    assert unquote(qs["location"][0]) == MYWAVE_VENUE["location_label"]
    assert "20260720T070000Z/20260720T073000Z" in qs["dates"][0]
