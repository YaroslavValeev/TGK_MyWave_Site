"""Services section order on home page."""

import pytest


@pytest.fixture
def home_mocks(mocker):
    mocker.patch("app.services.competitions.store.get_ticker_items", return_value=[])
    mocker.patch("app.services.blog.store.get_posts", return_value=([], 0))


def test_home_services_boat_before_gym(client, home_mocks):
    html = client.get("/").get_data(as_text=True)
    services_start = html.find('id="services"')
    assert services_start != -1
    section = html[services_start:]
    boat_pos = section.find('data-service="boat"')
    gym_pos = section.find('data-service="gym"')
    assert boat_pos != -1
    assert gym_pos != -1
    assert boat_pos < gym_pos
