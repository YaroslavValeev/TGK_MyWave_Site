"""PR77 — home content (25+ лет) and competitions ticker touch drag."""

from pathlib import Path


def test_home_professionalism_shows_25_years(client):
    html = client.get("/").get_data(as_text=True)
    assert "25+ лет" in html
    assert "23+ лет" not in html
    assert "Профессионализм" in html


def test_no_visible_23_plus_in_templates():
    templates = Path("templates").rglob("*.html")
    hits = []
    for path in templates:
        text = path.read_text(encoding="utf-8")
        if "23+" in text:
            hits.append(str(path))
    assert hits == [], f"unexpected 23+ in templates: {hits}"


def test_competitions_ticker_touch_drag_support():
    js = Path("static/js/competitions-ticker.js").read_text(encoding="utf-8")
    css = Path("static/css/competitions-ticker.css").read_text(encoding="utf-8")

    assert "pointerdown" in js
    assert "syncAnimationFromTranslate" in js
    assert "setManualTranslate" in js
    assert "is-dragging" in js
    assert "viewport.scrollLeft" not in js

    assert "touch-action: pan-x" in css
    assert "is-dragging a" in css.replace("\n", " ")


def test_index_loads_competitions_ticker_v9(client):
    html = client.get("/").get_data(as_text=True)
    assert "competitions-ticker.js?v=9" in html
    assert "competitions-ticker.css?v=9" in html
