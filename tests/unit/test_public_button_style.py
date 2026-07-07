"""Public CTA button system — white outline, turquoise border."""

from pathlib import Path


def _button_block(css: str) -> str:
    start = css.find("Buttons (unified public CTA")
    assert start != -1, "unified public CTA block missing in branding.css"
    end = css.find("Cards (unified)", start)
    return css[start:end]


def test_branding_public_cta_tokens_and_shape():
    css = Path("static/css/branding.css").read_text(encoding="utf-8")
    block = _button_block(css)

    assert "--mw-cta-border: #00bcd4" in css
    assert "--mw-cta-text: #1f1f1f" in css
    assert "--mw-cta-bg: #ffffff" in css
    assert "border-radius: var(--mw-cta-radius)" in block
    assert "1.5px solid var(--mw-cta-border)" in block
    assert "border-radius: 999px" not in block


def test_style_css_does_not_override_public_cta_fill():
    css = Path("static/css/style.css").read_text(encoding="utf-8")
    assert "background-color: #00BCD4 !important" not in css
    assert "background-color: #007bff" not in css


def test_base_html_cache_bust_for_public_cta():
    base = Path("templates/base.html").read_text(encoding="utf-8")
    assert "?v=public-cta2" in base
    assert "css/branding.css" in base
    assert "css/style.css" in base


def test_hero_book_now_has_emphasized_glass_outline():
    css = Path("static/css/branding.css").read_text(encoding="utf-8")
    assert ".hero-section .btn-primary.book-now" in css
    assert "border-width: 2.5px" in css
    assert "backdrop-filter: blur" in css
    assert "rgba(255, 255, 255, 0.52)" in css
    hero_block = css.split(".hero-section .btn-primary.book-now", 1)[1].split(".brand-logo--footer", 1)[0]
    assert "background: var(--mw-brand)" not in hero_block
    assert "#35C0CD" not in hero_block or "border-color" in hero_block


def test_home_preserves_ticker_lockup_and_25_years(client):
    html = client.get("/").get_data(as_text=True)
    assert "competitions-ticker.js?v=11" in html
    assert "25+ лет" in html
    assert "mywave-x-loaded-black-lockup.png" in html
