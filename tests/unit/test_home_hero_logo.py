"""Home page hero logo layout (brand turquoise SVG)."""

import pytest


@pytest.fixture
def home_mocks(mocker):
    mocker.patch("app.services.competitions.store.get_ticker_items", return_value=[])
    mocker.patch("app.services.blog.store.get_posts", return_value=([], 0))


def test_home_renders_turquoise_hero_logo(client, home_mocks):
    html = client.get("/").get_data(as_text=True)
    assert "hero-title--logo" in html
    assert "brand-logo--hero" in html
    assert "MyWave_logo_turquoise.svg" in html
    assert "brand-logo--header" in html
    assert "brand-logo--footer" in html


def test_branding_css_hero_clearance_under_header():
    from pathlib import Path

    css = Path("static/css/branding.css").read_text(encoding="utf-8")
    assert "margin-top: -18px !important" in css
    assert "brand-logo--hero" in css
    assert ".hero-section.relative-section" in css
