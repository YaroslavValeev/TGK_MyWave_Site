"""Unit tests for YCLIENTS provider + helpers."""

from __future__ import annotations

import json
from urllib.error import HTTPError
from io import BytesIO

import pytest

from app.services.booking.providers.yclients import (
    YclientsApiError,
    YclientsNotConfiguredError,
    YclientsReadOnlyError,
    build_source_comment,
    get_yclients_provider,
    parse_attendance_status,
)
from app.services.booking.yclients_sync import handle_webhook_payload, normalize_webhook_record


def test_yclients_disabled_by_default(monkeypatch):
    monkeypatch.delenv("YCLIENTS_ENABLED", raising=False)
    provider = get_yclients_provider()
    assert provider.is_enabled() is False
    with pytest.raises(YclientsNotConfiguredError):
        provider.fetch_available_slots("2026-07-14")


def test_yclients_enabled_without_credentials(monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_READ_ONLY_ENABLED", "1")
    monkeypatch.delenv("YCLIENTS_PARTNER_TOKEN", raising=False)
    monkeypatch.delenv("YCLIENTS_USER_TOKEN", raising=False)
    provider = get_yclients_provider()
    assert provider.is_enabled() is True
    with pytest.raises(YclientsNotConfiguredError):
        provider._require_enabled()


def test_write_requires_flag(monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_WRITE_ENABLED", "0")
    monkeypatch.setenv("YCLIENTS_PARTNER_TOKEN", "p")
    monkeypatch.setenv("YCLIENTS_USER_TOKEN", "u")
    provider = get_yclients_provider()
    with pytest.raises(YclientsReadOnlyError):
        provider._require_write()


def test_auth_header_combines_tokens(monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_PARTNER_TOKEN", "PARTNER")
    monkeypatch.setenv("YCLIENTS_USER_TOKEN", "USERTOK")
    provider = get_yclients_provider()
    headers = provider._headers(need_user=True)
    assert headers["Authorization"] == "Bearer PARTNER, User USERTOK"
    assert headers["Accept"] == "application/vnd.yclients.v2+json"


def test_source_comment_and_attendance():
    assert "mw_source=telegram" in build_source_comment(source="telegram", internal_id="abc")
    assert parse_attendance_status(-1) == "cancelled"
    assert parse_attendance_status(0) == "waiting"
    assert parse_attendance_status(1, deleted=True) == "deleted"


def test_normalize_webhook_record_envelope():
    payload = {
        "company_id": 2043174,
        "resource": "record",
        "resource_id": 99,
        "status": "create",
        "data": {"id": 99, "attendance": 0, "date": "2026-07-29 10:00:00"},
    }
    normalized = normalize_webhook_record(payload)
    assert normalized["record_id"] == "99"
    assert normalized["lifecycle"] == "waiting"
    assert normalized["event_status"] == "create"


def test_fetch_slots_parses_book_times(monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_READ_ONLY_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_PARTNER_TOKEN", "p")
    monkeypatch.setenv("YCLIENTS_STAFF_ID", "123")

    provider = get_yclients_provider()

    def fake_request(method, path, **kwargs):
        assert method == "GET"
        assert "/book_times/2043174/123/2026-07-29" in path
        return {
            "success": True,
            "data": [
                {"time": "10:00", "seance_length": 1800, "datetime": 1},
                {"time": "10:30", "seance_length": 1800, "datetime": 2},
            ],
        }

    monkeypatch.setattr(provider, "_request", fake_request)
    slots = provider.fetch_available_slots("2026-07-29")
    assert [s.start_time for s in slots] == ["10:00", "10:30"]
    assert slots[0].duration_minutes == 30


def test_create_journal_multi_set(monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_WRITE_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_PARTNER_TOKEN", "p")
    monkeypatch.setenv("YCLIENTS_USER_TOKEN", "u")
    monkeypatch.setenv("YCLIENTS_STAFF_ID", "55")
    monkeypatch.setenv("YCLIENTS_SERVICE_IDS", "77")
    monkeypatch.setenv("BOAT_SLOT_DURATION_MINUTES", "30")
    monkeypatch.setenv("BOAT_SEANCE_MINUTES", "25")

    provider = get_yclients_provider()
    captured = {}

    def fake_request(method, path, **kwargs):
        captured["method"] = method
        captured["path"] = path
        captured["body"] = kwargs.get("body")
        return {"success": True, "data": [{"id": 999, "attendance": 0}]}

    monkeypatch.setattr(provider, "_request", fake_request)
    result = provider.create_booking(
        date_str="2026-07-29",
        time_str="10:00",
        client_name="Ivan",
        client_phone="+7 (916) 011-71-79",
        set_count=2,
        source="telegram",
        internal_id="mw-1",
        use_online=False,
    )
    assert result.external_id == "999"
    assert captured["method"] == "POST"
    assert captured["path"] == "/records/2043174"
    # 2 sets × 25 min seance (ride); slot occupancy 30 is for GCal/UI
    assert captured["body"]["seance_length"] == 3000
    assert "mw_source=telegram" in captured["body"]["comment"]
    assert captured["body"]["api_id"] == "mw-1"
    assert captured["body"]["client"]["phone"] == "79160117179"


def test_http_error_wrapped(monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_PARTNER_TOKEN", "p")
    provider = get_yclients_provider()

    class FakeHTTPError(HTTPError):
        def __init__(self):
            super().__init__(
                url="https://api.yclients.com/x",
                code=422,
                msg="unprocessable",
                hdrs=None,
                fp=BytesIO(json.dumps({"meta": {"message": "busy"}}).encode()),
            )

    def boom(*args, **kwargs):
        raise FakeHTTPError()

    monkeypatch.setattr(
        "app.services.booking.providers.yclients.urlopen",
        boom,
    )
    with pytest.raises(YclientsApiError) as exc:
        provider._request("GET", "/company/2043174/")
    assert exc.value.status == 422


def test_handle_webhook_ignores_non_record():
    result = handle_webhook_payload(
        {"company_id": 1, "resource": "goods_operations_sale", "status": "create", "data": {}}
    )
    assert result["status"] == "ignored"
