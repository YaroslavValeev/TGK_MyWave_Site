"""E2E: competitions ticker autoplay on mobile viewport (CSS transform)."""

import pytest

pytestmark = pytest.mark.e2e


@pytest.fixture
def ticker_items():
    return [
        {
            "id": "e1",
            "label": "Wakesurf · Test Cup · Orlando, USA · 01.08–03.08.2026",
            "href": "https://example.com",
            "is_live": False,
        },
        {
            "id": "e2",
            "label": "Wakeboard · Demo Open · Berlin, DE · 12.09–14.09.2026",
            "href": "https://example.org",
            "is_live": True,
        },
    ]


def _track_transform(page):
    return page.evaluate(
        """() => {
        const track = document.querySelector('.home-competitions-ticker__track');
        if (!track) return null;
        const style = window.getComputedStyle(track);
        return {
            transform: style.transform,
            animationName: style.animationName,
            animationDuration: style.animationDuration,
            animationPlayState: style.animationPlayState,
        };
    }"""
    )


def test_mobile_ticker_css_animation_moves_without_swipe(page, live_server, mocker, ticker_items):
    mocker.patch(
        "app.services.competitions.store.get_ticker_items",
        return_value=ticker_items,
    )
    mocker.patch(
        "app.services.blog.store.get_posts",
        return_value=([], 0),
    )

    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(live_server + "/", wait_until="networkidle")

    viewport = page.locator(".home-competitions-ticker__viewport")
    assert viewport.count() == 1
    assert viewport.first.evaluate("el => el.classList.contains('is-autoplay')") is True

    before = _track_transform(page)
    assert before is not None
    assert before["animationName"] == "competitions-ticker-marquee"
    assert "840s" in before["animationDuration"]
    assert before["animationPlayState"] == "running"

    page.wait_for_timeout(2500)

    after = _track_transform(page)
    assert after["transform"] != before["transform"]
    assert after["animationPlayState"] == "running"
