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


def test_boat_card_shows_partner_logos(client):
    html = client.get("/").get_data(as_text=True)
    assert 'aria-label="MyWave X Loaded"' in html
    assert 'alt="MyWave"' in html
    assert 'alt="Loaded"' in html
    assert "MyWave_logo_black.svg" in html
    assert "Loaded_logo_black.svg" in html
    assert html.count('class="boat-partner-logos"') == 1


def test_boat_partner_logos_only_for_boat_service():
    index = Path("templates/index.html").read_text(encoding="utf-8")
    assert "service.service_id == 'boat'" in index
    assert "boat_partner_logos.html" in index
    page = Path("page.html").read_text(encoding="utf-8")
    assert "boat-partner-logos" in page
    assert "MyWave_logo_black.svg" in page


def test_boat_partner_logos_styles():
    css = Path("static/css/style.css").read_text(encoding="utf-8")
    assert ".boat-partner-logos" in css
    assert ".boat-partner-logos__x" in css


def test_mywave_black_logo_asset_exists():
    path = Path(
        "static/images/logotip_MyWave/MyWave_logo_package_brand_turquoise/"
        "01_master/MyWave_logo_black.svg"
    )
    assert path.is_file()

