"""Online Coaching media endpoint and workflow tests."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple
from unittest.mock import patch

import pytest

from app.services.online_coaching_notifications import (
    format_materials_received_message,
    notify_materials_received,
    sanitize_record_for_telegram,
)
from app.services.online_coaching_schema import normalize_video_urls, validate_video_urls
from app.services.online_coaching_schema import (
    MEDIA_FILES_HEADERS,
    ONLINE_DIARIES_HEADERS,
    ONLINE_FOLLOWUPS_HEADERS,
    ONLINE_REQUESTS_HEADERS,
)
from app.services.online_coaching_store import (
    append_online_request,
    append_request_media,
    build_status_transition_fields,
    list_media_for_request,
    validate_media_payload,
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
    }
    base.update(overrides)
    return base


def _media_payload(**overrides: Any) -> Dict[str, Any]:
    base = {
        "video_urls": ["https://drive.google.com/file/1", "https://disk.yandex.ru/i/abc"],
        "review_task": "Разобрать стойку",
        "training_comment": "Ветер сильный, не держусь в волне",
        "training_date": "2026-07-06",
        "spot_or_location": "Паттайя",
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


def test_normalize_and_validate_video_urls():
    urls = normalize_video_urls([" https://a.com ", "", "https://b.com"])
    assert urls == ["https://a.com", "https://b.com"]
    assert validate_video_urls(urls) == []
    assert "invalid:video_url_scheme" in validate_video_urls(["ftp://bad.com"])
    assert "required:video_urls" in validate_video_urls([])


def test_validate_media_payload_requires_task_and_comment():
    errors = validate_media_payload({"video_urls": ["https://example.com/v.mp4"]})
    assert "required:review_task" in errors
    assert "required:training_comment" in errors


def test_append_online_request_video_check_always_waiting_video(fake_store, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": "cli_test"})(),
    )
    result = append_online_request(
        _sample_payload(video_url="https://example.com/ignored.mp4"),
        online_request_id="oc_req_abc123456789abcd",
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )
    assert result.request_status == "waiting_video"
    assert len(fake_store.rows.get("Media_Files", [])) == 0


def test_append_request_media_updates_request_and_media_files(fake_store, monkeypatch):
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": "cli_test"})(),
    )
    req_id = "oc_req_abc123456789abcd"
    append_online_request(
        _sample_payload(),
        online_request_id=req_id,
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )

    updated = append_request_media(
        req_id,
        _media_payload(),
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        sheet_update=fake_store.update,
    )
    assert updated["request_status"] == "video_received"
    assert updated["review_task"] == "Разобрать стойку"
    assert updated["deadline_at"]
    assert len(fake_store.rows.get("Media_Files", [])) == 2
    media = list_media_for_request(req_id, sheet_records=fake_store.records)
    assert len(media) == 2


def test_append_request_media_rejects_empty_urls(fake_store, monkeypatch):
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
    with pytest.raises(ValueError) as exc:
        append_request_media(
            req_id,
            _media_payload(video_urls=[]),
            sheet_records=fake_store.records,
            sheet_update=fake_store.update,
        )
    assert "required:video_urls" in str(exc.value)


def test_materials_telegram_message_includes_links_and_masks_pii():
    record = {
        "online_request_id": "oc_req_test1234567890",
        "service_type": "video_check",
        "name": "Ivan",
        "phone": "+79161234567",
        "preferred_channel": "telegram",
        "telegram_username": "@ivan",
        "discipline": "wakesurf",
        "level": "intermediate",
        "injuries_or_limits": "больное колено",
        "review_task": "Разобрать стойку",
        "training_comment": "Сильный ветер",
        "request_status": "video_received",
        "payment_required_timing": "after_service",
    }
    urls = ["https://drive.google.com/v1", "https://disk.yandex.ru/v2"]
    text = format_materials_received_message(record, video_urls=urls)
    assert "https://drive.google.com/v1" in text
    assert "https://disk.yandex.ru/v2" in text
    assert "Разобрать стойку" in text
    assert "Сильный ветер" in text
    assert "колено" not in text
    assert "79161234567" not in text
    safe = sanitize_record_for_telegram(record)
    assert safe["health_limits"] == "указаны"


@patch("app.services.online_coaching_notifications.send_telegram_notification_with_keyboard", return_value=True)
def test_notify_materials_includes_video_buttons(mock_send):
    record = {
        "online_request_id": "oc_req_test1234567890",
        "service_type": "video_check",
        "name": "Ivan",
        "phone": "+79161234567",
        "preferred_channel": "telegram",
        "telegram_username": "@ivan",
        "request_status": "video_received",
        "payment_required_timing": "after_service",
        "review_task": "Задача",
        "training_comment": "Коммент",
    }
    urls = ["https://a.com/1", "https://b.com/2"]
    assert notify_materials_received(record, video_urls=urls) is True
    keyboard = mock_send.call_args[0][1]
    assert any(btn.get("text") == "Видео 1" for row in keyboard for btn in row)
    assert any(btn.get("text") == "Открыть заявку" for row in keyboard for btn in row)


def test_build_status_transition_in_review_sets_timestamp():
    fields = build_status_transition_fields("in_review")
    assert fields["request_status"] == "in_review"
    assert fields["in_review_at"]
    assert fields["next_followup_at"]


@pytest.fixture()
def oc_client(monkeypatch):
    monkeypatch.setenv("ONLINE_COACHING_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_APPLICATIONS_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_ADMIN_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_NOTIFICATIONS_ENABLED", "0")
    monkeypatch.setenv("DISABLE_TELEGRAM", "1")
    monkeypatch.setenv("SPREADSHEET_ID", "fake-sheet-id")

    from app import create_app

    app = create_app("development")
    app.config["TESTING"] = True
    app.config["WTF_CSRF_ENABLED"] = False
    with app.test_client() as client:
        yield client


@patch("app.routes.online_coaching.append_online_request")
def test_apply_returns_online_request_id_and_video_step(mock_append, oc_client):
    mock_append.return_value = type(
        "R",
        (),
        {
            "online_request_id": "oc_req_abc123456789abcd",
            "request_status": "waiting_video",
            "payment_required_timing": "after_service",
        },
    )()
    resp = oc_client.post(
        "/api/online-coaching/apply",
        json=_sample_payload(),
    )
    assert resp.status_code == 201
    data = resp.get_json()
    assert data["online_request_id"] == "oc_req_abc123456789abcd"
    assert data["show_video_step"] is True


@patch("app.routes.online_coaching.append_request_media")
def test_media_endpoint_success(mock_media, oc_client):
    mock_media.return_value = {
        "online_request_id": "oc_req_abc123456789abcd",
        "request_status": "video_received",
        "video_urls": ["https://example.com/v.mp4"],
    }
    resp = oc_client.post(
        "/api/online-coaching/oc_req_abc123456789abcd/media",
        json=_media_payload(video_urls=["https://example.com/v.mp4"]),
    )
    assert resp.status_code == 200
    data = resp.get_json()
    assert data["ok"] is True
    assert data["status"] == "video_received"


def test_media_endpoint_rejects_invalid_url(oc_client):
    resp = oc_client.post(
        "/api/online-coaching/oc_req_abc123456789abcd/media",
        json=_media_payload(video_urls=["javascript:alert(1)"]),
    )
    assert resp.status_code == 400


def test_online_coaching_page_has_video_step_markup(oc_client):
    resp = oc_client.get("/services/online-coaching")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert 'id="oc-apply-success"' in html
    assert 'id="oc-video-form"' in html
    assert 'id="oc-video-done"' in html
