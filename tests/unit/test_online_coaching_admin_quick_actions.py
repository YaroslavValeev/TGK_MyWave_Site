"""Admin Online Coaching — quick action workflow (POST + status transitions)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

REQ_ID = "oc_req_abc123456789abcd"


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


def _base_record(**overrides):
    row = {
        "online_request_id": REQ_ID,
        "service_type": "video_check",
        "request_status": "video_received",
        "name": "Test",
        "phone": "+79161234567",
        "client_id": "cli_1",
    }
    row.update(overrides)
    return row


def _post_quick_action(client, action: str):
    detail = client.get(f"/admin/online-coaching/{REQ_ID}")
    assert detail.status_code == 200
    return client.post(
        f"/admin/online-coaching/{REQ_ID}/quick-action",
        data={"action": action},
        follow_redirects=False,
    )


@pytest.mark.parametrize(
    "action,expected_status",
    [
        ("request_video", "waiting_video"),
        ("start_review", "in_review"),
        ("review_sent", "review_sent"),
        ("waiting_payment", "waiting_payment"),
        ("complete", "completed"),
        ("cancel_test", "cancelled"),
    ],
)
def test_quick_actions_update_status(oc_admin_client, mocker, action, expected_status):
    mocker.patch(
        "app.routes.admin.online_coaching.get_online_request_detail",
        side_effect=[
            _base_record(),
            _base_record(request_status=expected_status),
        ],
    )
    mocker.patch("app.routes.admin.online_coaching.list_media_for_request", return_value=[])
    updated = _base_record(request_status=expected_status)
    update_mock = mocker.patch(
        "app.routes.admin.online_coaching.update_request_fields",
        return_value=updated,
    )
    mocker.patch("app.routes.admin.online_coaching.log_admin_action")

    resp = _post_quick_action(oc_admin_client, action)
    assert resp.status_code == 302
    assert REQ_ID in (resp.location or "")
    assert update_mock.called
    fields = update_mock.call_args[0][1]
    assert fields["request_status"] == expected_status


def test_quick_action_mark_paid(oc_admin_client, mocker):
    mocker.patch(
        "app.routes.admin.online_coaching.get_online_request_detail",
        return_value=_base_record(),
    )
    mocker.patch(
        "app.routes.admin.online_coaching.mark_paid",
        return_value={"amount": 1500, "request": _base_record(request_status="paid")},
    )
    mocker.patch("app.routes.admin.online_coaching.log_admin_action")

    resp = _post_quick_action(oc_admin_client, "mark_paid")
    assert resp.status_code == 302


def test_change_status_get_not_allowed(oc_admin_client, mocker):
    mocker.patch(
        "app.routes.admin.online_coaching.get_online_request_detail",
        return_value=_base_record(),
    )
    resp = oc_admin_client.get(
        f"/admin/online-coaching/{REQ_ID}/quick-action",
        follow_redirects=False,
    )
    assert resp.status_code == 405
