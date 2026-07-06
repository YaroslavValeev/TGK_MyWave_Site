"""PR53.4.1 / PR82 — native scroll competitions ticker autoplay."""

from pathlib import Path


def test_competitions_ticker_uses_native_scroll_autoplay():
    js = Path("static/js/competitions-ticker.js").read_text(encoding="utf-8")
    css = Path("static/css/competitions-ticker.css").read_text(encoding="utf-8")

    assert "scrollLeft" in js
    assert "cycleWidth" in js
    assert "requestAnimationFrame" in js
    assert "passive: true" in js
    assert "AUTO_SPEED_PX_PER_SEC" in js
    assert "MOMENTUM_FRICTION" in js
    assert "MOBILE_AUTO_SCROLL" not in js
    assert "setManualTranslate" not in js
    assert "syncAnimationFromTranslate" not in js
    assert "--ticker-duration" not in js
    assert "840" not in js

    assert "overflow-x: auto" in css
    assert "-webkit-overflow-scrolling: touch" in css
    assert "touch-action: pan-x pan-y" in css
    assert "competitions-ticker-marquee" not in css
    assert "translateX(-50%)" not in css


def test_index_loads_competitions_ticker_v11(client):
    html = client.get("/").get_data(as_text=True)
    assert "competitions-ticker.js?v=11" in html
    assert "competitions-ticker.css?v=11" in html


def test_pr534_footer_and_notify_regressions():
    """PR53.4 scope must not regress."""
    branding = Path("static/css/branding.css").read_text(encoding="utf-8")
    notify = Path("app/services/application_notifications.py").read_text(encoding="utf-8")
    assert "site-footer__link" in branding
    assert "_normalize_lead_status" in notify
