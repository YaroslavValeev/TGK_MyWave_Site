"""Public Online Coaching copy guards (Release S1)."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OC_TEMPLATE = REPO_ROOT / "templates" / "services" / "online_coaching.html"


def test_progress_month_public_price_uses_month_unit():
    html = OC_TEMPLATE.read_text(encoding="utf-8")
    assert "12 000 ₽ / месяц" in html
    assert "12 000 ₽ / сет" not in html


def test_oc_film_first_tip_from_boat():
    html = OC_TEMPLATE.read_text(encoding="utf-8")
    film_start = html.index('id="oc-film"')
    film_block = html[film_start : film_start + 1200]
    assert "<li>Из катера снимать на 1х.</li>" in film_block
    assert "Стабильная камера или штатив" not in film_block


def test_oc_included_has_mobile_cards_without_scroll_hint():
    html = OC_TEMPLATE.read_text(encoding="utf-8")
    assert "oc-included-mobile" in html
    assert "oc-included-desktop" in html
    assert "oc-page--chat-safe" in html
    assert 'id="oc-prices"' not in html


def test_oc_faq_does_not_promote_extra_channels():
    html = OC_TEMPLATE.read_text(encoding="utf-8")
    faq_start = html.index('id="oc-faq"')
    faq_block = html[faq_start : faq_start + 1800]
    assert "WhatsApp" not in faq_block
    assert "MAX" not in faq_block
