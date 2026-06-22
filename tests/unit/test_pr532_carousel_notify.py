"""PR53.2 evidence — competitions mobile autoplay + Telegram status."""

from pathlib import Path
from unittest.mock import MagicMock

from app.services.application_notifications import (
    _normalize_lead_status,
    format_application_telegram_message,
)


def test_mobile_autoscroll_enabled_in_js():
    js = Path("static/js/competitions-ticker.js").read_text(encoding="utf-8")
    assert "MOBILE_AUTO_SCROLL = true" in js
    assert "BASE_DURATION_SEC = 840" in js


def test_telegram_status_rejects_magicmock():
    mock_status = MagicMock(name="save_product_lead().status")
    text = format_application_telegram_message(
        "product",
        {
            "name": "Test",
            "phone": "+7 916 000 00 01",
            "product_title": "Board",
            "status": mock_status,
        },
    )
    assert "MagicMock" not in text
    assert "Статус: new" in text


def test_normalize_lead_status_human():
    assert _normalize_lead_status("new") == "new"
    assert _normalize_lead_status(MagicMock()) == "new"
