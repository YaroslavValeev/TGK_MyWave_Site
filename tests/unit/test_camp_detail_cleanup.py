"""Очистка описания/галереи кемпа из Tour перед показом на /camps/<id>."""

from app.services.camps.normalize import normalize_tour_camp
from app.services.camps.showcase import to_showcase_view

FULL = "Друзья, мы едем закрывать сезон! Остались места на даты 25-31 октября. Проживание в доме с баней."
SHORT = "Друзья, мы едем закрывать сезон! Остались места…"
INCLUDED = "Базовая программа и сопровождение организатора."
NOTE = "Требует ручного заполнения оператором."


def _raw(**overrides):
    raw = {
        "id": "tour_camp_1",
        "title": "Кемп",
        "short_description": SHORT,
        "description": f"{FULL} {SHORT} {INCLUDED} {NOTE} {NOTE}",
        "included": [INCLUDED],
        "cover_image_url": "https://mywavetour.ru/a.jpg",
        "gallery": ["https://mywavetour.ru/a.jpg", "https://mywavetour.ru/b.jpg"],
    }
    raw.update(overrides)
    return raw


def test_included_list_is_joined_not_repr():
    norm = normalize_tour_camp(_raw(included=["Проживание", "Катание"]))
    assert norm["included"] == "Проживание\nКатание"


def test_description_drops_duplicates_and_operator_notes():
    view = to_showcase_view(_raw())
    assert view["description"] == FULL
    assert view["included"] == INCLUDED


def test_description_drops_short_with_collapsed_newlines():
    full = "Заезд в 14:00\n-питание: завтрак\n-проживание в доме"
    short = "Заезд в 14:00 -питание: завтрак -прожив …"
    view = to_showcase_view(_raw(description=f"{full} {short}", short_description=short, included=None))
    assert view["description"] == full
    assert view["short_description"] is None


def test_short_description_hidden_when_description_repeats_it():
    view = to_showcase_view(_raw())
    assert view["short_description"] is None


def test_short_description_kept_when_distinct():
    view = to_showcase_view(_raw(short_description="Осенний кемп в Краснодаре", description="Подробности программы."))
    assert view["short_description"] == "Осенний кемп в Краснодаре"
    assert view["description"] == "Подробности программы."


def test_gallery_skips_cover_duplicate():
    view = to_showcase_view(_raw())
    assert view["gallery"] == ["https://mywavetour.ru/b.jpg"]
