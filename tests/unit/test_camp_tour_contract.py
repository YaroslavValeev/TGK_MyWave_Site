"""Контракт Tour Camp API (ответ Tour 25.09.2026): sport/audience — массивы, пагинация до next_offset=null."""

from datetime import date
from unittest import mock

from app.services.camps import tour_client
from app.services.camps.showcase import is_showcase_public, to_showcase_view

TODAY = date(2026, 9, 25)

TOUR_EXAMPLE = {
    "id": "tour_cmxxxxxxxxxxxxxxx",
    "title": "Вейксерф-кемп на Волге",
    "sport": ["wakesurf"],
    "start_date": "2027-06-10",
    "end_date": "2027-06-16",
    "publication_status": "published",
    "content_rights_status": "unknown",
    "audience_language": ["ru"],
    "cover_image_url": "https://mywavetour.ru/ingestion-media/example.jpg",
    "booking_url": "https://example.com/book",
}


def test_tour_example_camp_is_public():
    assert is_showcase_public(TOUR_EXAMPLE, today=TODAY)


def test_sport_list_with_both_disciplines_is_public_and_mixed():
    camp = {**TOUR_EXAMPLE, "sport": ["wakesurf", "wakeboard"]}
    assert is_showcase_public(camp, today=TODAY)
    assert to_showcase_view(camp)["sport"] == "mixed"


def test_non_wake_sport_list_is_hidden():
    assert not is_showcase_public({**TOUR_EXAMPLE, "sport": ["kitesurf"]}, today=TODAY)


def test_finished_camp_is_hidden():
    camp = {**TOUR_EXAMPLE, "start_date": "2026-08-01", "end_date": "2026-08-07"}
    assert not is_showcase_public(camp, today=TODAY)


def test_pagination_continues_through_empty_page_until_null():
    pages = {
        0: ([], 25),
        25: ([TOUR_EXAMPLE], 50),
        50: ([], None),
    }
    calls = []

    def fake_page(*, offset=None, **_kwargs):
        calls.append(offset)
        return pages[offset]

    with mock.patch.object(tour_client, "fetch_tour_camps_page", side_effect=fake_page):
        items = tour_client.fetch_tour_camps(use_pagination=True, feed_url="")

    assert calls == [0, 25, 50]
    assert items == [TOUR_EXAMPLE]
