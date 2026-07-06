"""Online Coaching store layer tests (mocked Sheets)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pytest

from app.services.online_coaching_schema import (
    ONLINE_DIARIES_HEADERS,
    ONLINE_FOLLOWUPS_HEADERS,
    ONLINE_REQUESTS_HEADERS,
    MEDIA_FILES_HEADERS,
)
from app.services.online_coaching_store import (
    append_diary_entry,
    append_followup,
    append_online_request,
    build_request_row,
    parse_application_input,
    resolve_initial_status,
    update_request_fields,
    validate_application_payload,
)


def _sample_payload(**overrides: Any) -> Dict[str, Any]:
    base = {
        "name": "Ivan",
        "phone": "+79161234567",
        "service_type": "video_check",
        "preferred_channel": "telegram",
        "telegram_username": "@ivan",
        "consent_personal_data": True,
        "consent_version": "2026-07-v1",
        "video_url": "https://example.com/v.mp4",
    }
    base.update(overrides)
    return base


class FakeSheetStore:
    def __init__(self) -> None:
        self.rows: Dict[str, List[List[str]]] = {}
        self.updates: List[Tuple[str, str, str, List[str]]] = []

    def append(self, spreadsheet_id: str, sheet_name: str, values: List[str]) -> None:
        self.rows.setdefault(sheet_name, []).append(values)

    def records(self, spreadsheet_id: str, sheet_name: str) -> Sequence[Mapping[str, Any]]:
        headers_map = {
            "Online_Requests": ONLINE_REQUESTS_HEADERS,
            "Online_Diaries": ONLINE_DIARIES_HEADERS,
            "Online_Followups": ONLINE_FOLLOWUPS_HEADERS,
            "Media_Files": MEDIA_FILES_HEADERS,
        }
        headers = headers_map.get(sheet_name, ())
        out = []
        for row in self.rows.get(sheet_name, []):
            out.append({headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))})
        return out

    def update(self, spreadsheet_id: str, sheet_name: str, cell: str, values: List[str]) -> None:
        self.updates.append((spreadsheet_id, sheet_name, cell, values))


@pytest.fixture()
def fake_store(monkeypatch):
    store = FakeSheetStore()
    monkeypatch.setenv("SPREADSHEET_ID", "fake-sheet-id")
    return store


def test_build_request_row_video_check():
    payload = parse_application_input(_sample_payload())
    row = build_request_row("oc_req_abc123456789abcd", payload, request_status="waiting_video")
    assert row["service_type"] == "video_check"
    assert row["payment_required_timing"] == "after_service"
    assert row["request_status"] == "waiting_video"


def test_append_online_request_writes_request_and_media(fake_store, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": "cli_test"})(),
    )

    result = append_online_request(
        _sample_payload(),
        online_request_id="oc_req_abc123456789abcd",
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )

    assert result.online_request_id == "oc_req_abc123456789abcd"
    assert result.request_status == "video_received"
    assert len(fake_store.rows.get("Online_Requests", [])) == 1
    assert len(fake_store.rows.get("Media_Files", [])) == 1


def test_append_online_request_progress_month_waiting_payment(fake_store, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": ""})(),
    )

    result = append_online_request(
        _sample_payload(service_type="progress_month", video_url=""),
        online_request_id="oc_req_def4567890123456",
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )
    assert result.request_status == "waiting_payment"


def test_update_request_fields(fake_store, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": ""})(),
    )
    req_id = "oc_req_abc123456789abcd"
    append_online_request(
        _sample_payload(),
        online_request_id=req_id,
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )

    updated = update_request_fields(
        req_id,
        {"request_status": "in_review"},
        sheet_records=fake_store.records,
        sheet_update=fake_store.update,
    )
    assert updated["request_status"] == "in_review"
    assert fake_store.updates


def test_append_diary_entry(fake_store, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": "cli_1"})(),
    )
    req_id = "oc_req_abc123456789abcd"
    append_online_request(
        _sample_payload(),
        online_request_id=req_id,
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )

    diary_id = append_diary_entry(
        req_id,
        {"current_goal": "Стабильность", "water_task": "Практика"},
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        sheet_update=fake_store.update,
    )
    assert diary_id.startswith("oc_diary_")
    assert len(fake_store.rows.get("Online_Diaries", [])) == 1


def test_append_followup(fake_store, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": ""})(),
    )
    req_id = "oc_req_abc123456789abcd"
    append_online_request(
        _sample_payload(),
        online_request_id=req_id,
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )

    fu_id = append_followup(
        req_id,
        {"scheduled_at": "2026-07-10T12:00", "note": "Напомнить о видео"},
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        sheet_update=fake_store.update,
    )
    assert fu_id.startswith("oc_fu_")
    assert len(fake_store.rows.get("Online_Followups", [])) == 1


def test_validate_requires_telegram_when_channel_telegram():
    errors = validate_application_payload(
        _sample_payload(telegram_username="", preferred_channel="telegram")
    )
    assert "required:telegram_username" in errors


def test_resolve_initial_status_matrix():
    assert resolve_initial_status("live_coach_water", "") == "new"
    assert resolve_initial_status("video_check", "") == "waiting_video"
