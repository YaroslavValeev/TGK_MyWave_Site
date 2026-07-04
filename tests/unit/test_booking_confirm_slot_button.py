"""Booking step 2 — confirmSlotBtn must stay visible for boat multi-slot flow."""

from pathlib import Path


def test_confirm_slot_button_not_display_none_in_style_css():
    css = Path("static/css/style.css").read_text(encoding="utf-8")
    assert "#confirmSlotBtn" in css
    assert "display: none" not in css.split("#confirmSlotBtn")[1].split("}")[0]


def test_booking_mobile_css_shows_confirm_slot_button():
    css = Path("static/css/booking-mobile.css").read_text(encoding="utf-8")
    assert "#confirmSlotBtn" in css
    assert "display: block" in css or "min-height: 44px" in css
