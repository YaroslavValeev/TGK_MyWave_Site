"""Online Coaching schema validation tests."""

import re

import pytest

from app.services.online_coaching_schema import (
    MEDIA_FILES_SHEET,
    ONLINE_DIARIES_SHEET,
    ONLINE_FOLLOWUPS_SHEET,
    ONLINE_PAYMENTS_SHEET,
    ONLINE_REQUESTS_HEADERS,
    ONLINE_REQUESTS_SHEET,
    ONLINE_REVIEWS_SHEET,
    SERVICE_PRICES,
    SERVICE_PRICE_UNITS,
    SERVICE_TYPES,
    col_letter,
    format_service_price,
    payment_timing_for_service,
    validate_sheet_headers,
)
from app.services.online_coaching_store import generate_request_id, resolve_initial_status


class TestRequestId:
    def test_generate_request_id_format(self):
        req_id = generate_request_id()
        assert re.match(r"^oc_req_[0-9a-f]{16}$", req_id)


class TestInitialStatus:
    def test_progress_month_waiting_payment(self):
        assert resolve_initial_status("progress_month", "") == "waiting_payment"

    def test_video_check_without_video(self):
        assert resolve_initial_status("video_check", "") == "waiting_video"

    def test_video_check_with_video_still_waiting(self):
        assert resolve_initial_status("video_check", "https://example.com/v") == "waiting_video"

    def test_live_new(self):
        assert resolve_initial_status("live_coach_land", "") == "new"


class TestSchema:
    def test_col_letter_basic(self):
        assert col_letter(0) == "A"
        assert col_letter(25) == "Z"
        assert col_letter(26) == "AA"

    def test_validate_online_requests_headers_ok(self):
        ok, missing = validate_sheet_headers(ONLINE_REQUESTS_SHEET, ONLINE_REQUESTS_HEADERS)
        assert ok is True
        assert missing == []

    def test_validate_missing_header(self):
        ok, missing = validate_sheet_headers(ONLINE_REQUESTS_SHEET, ["online_request_id"])
        assert ok is False
        assert "created_at" in missing

    def test_service_prices_defined(self):
        for service in SERVICE_TYPES:
            assert service in SERVICE_PRICES
            assert SERVICE_PRICES[service] > 0

    def test_payment_timing_mapping(self):
        assert payment_timing_for_service("progress_month") == "upfront"
        assert payment_timing_for_service("video_check") == "after_service"

    def test_progress_month_price_unit_is_month(self):
        assert SERVICE_PRICE_UNITS["progress_month"] == "месяц"
        assert format_service_price("progress_month") == "12 000 ₽ / месяц"
        assert "сет" not in format_service_price("progress_month")

    def test_video_check_price_unit_is_set(self):
        assert format_service_price("video_check") == "1 500 ₽ / сет"

    def test_all_contract_sheets_known(self):
        for sheet in (
            ONLINE_REQUESTS_SHEET,
            ONLINE_DIARIES_SHEET,
            ONLINE_PAYMENTS_SHEET,
            ONLINE_REVIEWS_SHEET,
            ONLINE_FOLLOWUPS_SHEET,
            MEDIA_FILES_SHEET,
        ):
            ok, missing = validate_sheet_headers(sheet, [])
            assert ok is False
            assert missing
