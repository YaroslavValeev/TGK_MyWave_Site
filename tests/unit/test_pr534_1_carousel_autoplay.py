"""PR53.4.1 — real mobile competitions carousel autoplay (CSS transform)."""

from pathlib import Path


def test_competitions_ticker_uses_css_transform_autoplay():
    js = Path("static/js/competitions-ticker.js").read_text(encoding="utf-8")
    css = Path("static/css/competitions-ticker.css").read_text(encoding="utf-8")

    assert "is-autoplay" in js
    assert "pointerdown" in js
    assert "syncAnimationFromTranslate" in js
    assert "MOBILE_AUTO_SCROLL" not in js
    assert "viewport.scrollLeft" not in js
    assert "requestAnimationFrame" not in js
    assert "--ticker-duration" in js
    assert "840" in js

    assert "competitions-ticker-marquee" in css
    assert "translateX(-50%)" in css
    assert "animation-play-state: paused" in css
    assert "is-autoplay" in css


def test_index_loads_competitions_ticker_v8(client):
    html = client.get("/").get_data(as_text=True)
    assert "competitions-ticker.js?v=9" in html
    assert "competitions-ticker.css?v=9" in html


def test_pr534_footer_and_notify_regressions():
    """PR53.4 scope must not regress."""
    branding = Path("static/css/branding.css").read_text(encoding="utf-8")
    notify = Path("app/services/application_notifications.py").read_text(encoding="utf-8")
    assert "site-footer__link" in branding
    assert "_normalize_lead_status" in notify
