"""PR77/PR82 — home content (25+ лет), partner lockup, native ticker scroll."""

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


def test_competitions_ticker_native_scroll_support():
    js = Path("static/js/competitions-ticker.js").read_text(encoding="utf-8")
    css = Path("static/css/competitions-ticker.css").read_text(encoding="utf-8")

    assert "scrollLeft" in js
    assert "cycleWidth" in js
    assert "requestAnimationFrame" in js
    assert "passive: true" in js
    assert "setManualTranslate" not in js
    assert "syncAnimationFromTranslate" not in js
    assert "translateX(" not in js

    assert "overflow-x: auto" in css
    assert "-webkit-overflow-scrolling: touch" in css
    assert "touch-action: pan-x pan-y" in css
    assert "competitions-ticker-marquee" not in css
    assert "is-dragging a" in css.replace("\n", " ")


def test_index_loads_competitions_ticker_v11(client):
    html = client.get("/").get_data(as_text=True)
    assert "competitions-ticker.js?v=11" in html
    assert "competitions-ticker.css?v=11" in html


def test_boat_card_shows_partner_lockup(client):
    html = client.get("/").get_data(as_text=True)
    assert 'aria-label="MyWave X Loaded"' in html
    assert 'alt="MyWave X Loaded"' in html
    assert "mywave-x-loaded-black-lockup.png" in html
    assert "boat-partner-logos__lockup" in html
    assert html.count('class="boat-partner-logos"') == 1


def test_boat_partner_logos_only_for_boat_service():
    index = Path("templates/index.html").read_text(encoding="utf-8")
    assert "service.service_id == 'boat'" in index
    assert "boat_partner_logos.html" in index
    page = Path("page.html").read_text(encoding="utf-8")
    assert "boat-partner-logos__lockup" in page
    assert "mywave-x-loaded-black-lockup.png" in page


def test_boat_partner_logos_styles():
    css = Path("static/css/style.css").read_text(encoding="utf-8")
    assert ".boat-partner-logos" in css
    assert ".boat-partner-logos__lockup" in css
    assert ".boat-partner-logos__logo--mywave" not in css
    assert ".boat-partner-logos__x" not in css


def test_partner_lockup_asset_exists():
    png = Path("static/images/partners/mywave-x-loaded-black-lockup.png")
    assert png.is_file()
    assert png.stat().st_size > 10000


def test_mywave_black_logo_asset_exists():
    path = Path(
        "static/images/logotip_MyWave/MyWave_logo_package_brand_turquoise/"
        "01_master/MyWave_logo_black.svg"
    )
    assert path.is_file()


def test_loaded_logo_asset_exists():
    path = Path("static/images/Logotip_Loaded/Loaded_logo_black_site.svg")
    assert path.is_file()
