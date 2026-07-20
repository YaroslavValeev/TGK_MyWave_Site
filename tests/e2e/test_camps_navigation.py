"""E2E: navigation to /camps showcase."""

import pytest


@pytest.fixture
def camp_public(mocker):
    mocker.patch("app.config.camp_features.is_camp_public_enabled", return_value=True)
    mocker.patch("app.routes.camps.is_camp_public_enabled", return_value=True)


def test_home_nav_link_to_camps(live_server, camp_public, mocker):
    import requests

    mocker.patch("app.services.camps.showcase.fetch_showcase_preview", return_value=[])
    mocker.patch(
        "app.services.camps.showcase.fetch_showcase_camps",
        return_value=type("R", (), {"state": "empty", "camps": [], "message": ""})(),
    )

    response = requests.get(live_server + "/", timeout=15)
    assert response.status_code == 200
    html = response.text
    assert "/camps" in html or "Все кемпы" in html


def test_camps_page_accessible(live_server, camp_public, mocker):
    import requests

    mvp = {
        "id": "tour_camp_api_mvp_wakesurf_v1",
        "title": "MVP Wakesurf Camp",
        "partnership_confirmed": False,
        "source_badge": "Из MyWaveTour",
        "availability_label": "Есть места",
        "sport_label": "Вейксерф",
    }
    mocker.patch(
        "app.routes.camps.fetch_showcase_camps",
        return_value=type("R", (), {"state": "ok", "camps": [mvp], "message": ""})(),
    )

    response = requests.get(live_server + "/camps", timeout=15)
    assert response.status_code == 200
    assert "MVP Wakesurf Camp" in response.text
    assert "tour_camp_api_mvp_wakesurf_v1" in response.text
