"""Admin Online Coaching — CSRF on POST forms (quick actions)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture()
def oc_admin_client(client, mocker, monkeypatch):
    monkeypatch.setenv("ONLINE_COACHING_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_ADMIN_ENABLED", "1")
    monkeypatch.setenv("ONLINE_COACHING_NOTIFICATIONS_ENABLED", "0")
    monkeypatch.setenv("DISABLE_TELEGRAM", "1")
    monkeypatch.setenv("SPREADSHEET_ID", "fake-sheet-id")

    user = MagicMock()
    user.is_authenticated = True
    user.is_admin = True
    user.username = "oc_admin"
    user.email = "admin@example.com"
    user.get_id.return_value = "42"
    mocker.patch("flask_login.utils._get_user", return_value=user)
    with client.session_transaction() as sess:
        sess["_user_id"] = "42"
        sess["_fresh"] = True
    return client


def _sample_record():
    return {
        "online_request_id": "oc_req_abc123456789abcd",
        "service_type": "video_check",
        "request_status": "video_received",
        "name": "Test",
        "phone": "+79161234567",
        "client_id": "cli_1",
    }


def test_detail_quick_action_forms_include_csrf(oc_admin_client, mocker):
    mocker.patch(
        "app.routes.admin.online_coaching.get_online_request_detail",
        return_value=_sample_record(),
    )
    mocker.patch(
        "app.routes.admin.online_coaching.list_media_for_request",
        return_value=[],
    )

    resp = oc_admin_client.get("/admin/online-coaching/oc_req_abc123456789abcd")
    assert resp.status_code == 200
    html = resp.data.decode("utf-8")
    assert 'name="csrf_token"' in html
    assert "quick-action" in html or "quick_action" in html
    assert html.count('name="csrf_token"') >= 7


def test_quick_action_start_review_with_csrf_redirects(oc_admin_client, mocker):
    mocker.patch(
        "app.routes.admin.online_coaching.get_online_request_detail",
        side_effect=[
            _sample_record(),
            {**_sample_record(), "request_status": "in_review"},
        ],
    )
    mocker.patch(
        "app.routes.admin.online_coaching.list_media_for_request",
        return_value=[],
    )
    mocker.patch(
        "app.routes.admin.online_coaching.update_request_fields",
        return_value={**_sample_record(), "request_status": "in_review"},
    )
    mocker.patch("app.routes.admin.online_coaching.log_admin_action")

    detail = oc_admin_client.get("/admin/online-coaching/oc_req_abc123456789abcd")
    assert detail.status_code == 200

    resp = oc_admin_client.post(
        "/admin/online-coaching/oc_req_abc123456789abcd/quick-action",
        data={"action": "start_review"},
        follow_redirects=False,
    )
    assert resp.status_code == 302
    assert "oc_req_abc123456789abcd" in (resp.location or "")
