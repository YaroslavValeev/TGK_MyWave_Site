"""PR56 — Social manual session assign, status transitions, audit log."""

from unittest.mock import MagicMock, patch

import pytest

from app.services.application_notifications import (
    format_social_session_scheduled_message,
    notify_social_session_scheduled,
)
from app.services.social_schema import (
    SESSION_STATUSES,
    SOCIAL_AUDIT_LOG_HEADERS,
    SOCIAL_SESSIONS_HEADERS,
    SOCIAL_SESSIONS_SHEET,
    validate_sheet_headers,
)
from app.services.social_sessions import (
    append_social_audit_log,
    build_session_row,
    manual_assign_social_session,
    parse_assign_input,
    session_row_to_values,
    transition_social_session_status,
    validate_assign_payload,
)
from app.services.social_store import append_social_application


def _valid_assign(**overrides):
    base = {
        "application_id": "soc_app_aaaaaaaaaaaaaaaa",
        "session_date": "2026-07-15",
        "session_time": "10:00",
        "assigned_by": "trainer_ivan",
        "location": "Павильон",
        "service_type": "adaptive_wake",
        "coach": "Coach A",
        "notes": "Первая тренировка",
        "source": "manual_assign",
    }
    base.update(overrides)
    return base


def _fake_app_records(application_id: str, status: str = "new"):
    return [
        {
            "application_id": application_id,
            "status": status,
            "created_at": "2026-06-01T00:00:00Z",
        }
    ]


class TestSocialSessionsSchema:
    def test_sessions_headers_contract(self):
        ok, missing = validate_sheet_headers(
            SOCIAL_SESSIONS_SHEET,
            list(SOCIAL_SESSIONS_HEADERS),
        )
        assert ok is True
        assert missing == []

    def test_required_pr56_fields_present(self):
        required = {
            "session_id",
            "application_id",
            "created_at",
            "updated_at",
            "status",
            "assigned_by",
            "session_date",
            "session_time",
            "location",
            "service_type",
            "coach",
            "notes",
            "calendar_event_id",
            "booking_id",
            "source",
        }
        assert required == set(SOCIAL_SESSIONS_HEADERS)

    def test_session_statuses(self):
        assert SESSION_STATUSES == frozenset({"scheduled", "completed", "cancelled"})


class TestAssignValidation:
    def test_valid_assign_payload(self):
        assert validate_assign_payload(_valid_assign()) == []

    def test_missing_application_id(self):
        errors = validate_assign_payload(_valid_assign(application_id=""))
        assert "required:application_id" in errors

    def test_invalid_date_time(self):
        errors = validate_assign_payload(
            _valid_assign(session_date="15-07-2026", session_time="bad-time")
        )
        assert "invalid:session_date" in errors
        assert "invalid:session_time" in errors


class TestManualAssign:
    def test_manual_assign_creates_session_row(self):
        captured_sessions = []
        captured_apps = []
        captured_audit = []

        def fake_records(_sid, sheet_name):
            if sheet_name == "Social_Applications":
                return _fake_app_records("soc_app_aaaaaaaaaaaaaaaa", "approved")
            return []

        def fake_append(sid, sheet_name, values):
            if sheet_name == SOCIAL_SESSIONS_SHEET:
                captured_sessions.append(values)
            else:
                captured_audit.append((sheet_name, values))

        def fake_update(sid, sheet_name, cell, values):
            captured_apps.append((cell, values))

        result = manual_assign_social_session(
            _valid_assign(),
            session_id="soc_sess_bbbbbbbbbbbbbbbb",
            sheet_append=fake_append,
            sheet_update=fake_update,
            sheet_records=fake_records,
            audit_append=lambda *args, **kw: captured_audit.append(args) or "evt_1",
        )

        assert result.session_id == "soc_sess_bbbbbbbbbbbbbbbb"
        assert result.application_id == "soc_app_aaaaaaaaaaaaaaaa"
        assert result.status == "scheduled"
        assert len(captured_sessions) == 1
        row = dict(zip(SOCIAL_SESSIONS_HEADERS, captured_sessions[0]))
        assert row["status"] == "scheduled"
        assert row["application_id"] == "soc_app_aaaaaaaaaaaaaaaa"
        assert row["session_date"] == "2026-07-15"
        assert row["session_time"] == "10:00"
        assert row["assigned_by"] == "trainer_ivan"
        assert row["calendar_event_id"] == ""
        assert row["booking_id"] == ""

    def test_application_id_links_application_to_session(self):
        payload = parse_assign_input(_valid_assign())
        row = build_session_row("soc_sess_cccccccccccccccc", payload)
        values = session_row_to_values(row)
        idx_app = SOCIAL_SESSIONS_HEADERS.index("application_id")
        assert values[idx_app] == "soc_app_aaaaaaaaaaaaaaaa"

    def test_application_status_updated_to_scheduled(self):
        updates = []

        def fake_records(_sid, sheet_name):
            if sheet_name == "Social_Applications":
                return _fake_app_records("soc_app_dddddddddddddddd", "review")
            return []

        def fake_update(_sid, _sheet, cell, values):
            updates.append((cell, values))

        manual_assign_social_session(
            _valid_assign(application_id="soc_app_dddddddddddddddd"),
            session_id="soc_sess_eeeeeeeeeeeeeeee",
            sheet_append=lambda *_: None,
            sheet_update=fake_update,
            sheet_records=fake_records,
            audit_append=lambda *a, **k: "evt",
        )

        status_updates = [v for cell, v in updates if cell.startswith("D")]
        assert status_updates == [["scheduled"]]

    def test_not_assignable_application_rejected(self):
        def fake_records(_sid, sheet_name):
            if sheet_name == "Social_Applications":
                return _fake_app_records("soc_app_ffffffffffffffff", "rejected")
            return []

        with pytest.raises(ValueError, match="not_assignable"):
            manual_assign_social_session(
                _valid_assign(application_id="soc_app_ffffffffffffffff"),
                sheet_append=lambda *_: None,
                sheet_records=fake_records,
            )


class TestSessionTransitions:
    def _records_with_session(self, status: str = "scheduled"):
        return [
            {
                "session_id": "soc_sess_1111111111111111",
                "application_id": "soc_app_aaaaaaaaaaaaaaaa",
                "status": status,
            }
        ]

    def test_completed_transition(self):
        updates = []
        audit = []

        def fake_records(_sid, sheet_name):
            if sheet_name == SOCIAL_SESSIONS_SHEET:
                return self._records_with_session("scheduled")
            return []

        def fake_update(_sid, _sheet, cell, values):
            updates.append((cell, values))

        result = transition_social_session_status(
            "soc_sess_1111111111111111",
            "completed",
            actor="admin",
            sheet_update=fake_update,
            sheet_records=fake_records,
            audit_append=lambda *args, **kw: audit.append(args) or "evt",
        )

        assert result.old_status == "scheduled"
        assert result.new_status == "completed"
        status_updates = [v for cell, v in updates if cell.startswith("E")]
        assert status_updates == [["completed"]]
        assert audit[0][1] == "session_status_changed"

    def test_cancelled_transition(self):
        result = transition_social_session_status(
            "soc_sess_1111111111111111",
            "cancelled",
            actor="admin",
            sheet_update=lambda *_: None,
            sheet_records=lambda _sid, name: (
                self._records_with_session("scheduled")
                if name == SOCIAL_SESSIONS_SHEET
                else []
            ),
            audit_append=lambda *a, **k: "evt",
        )
        assert result.new_status == "cancelled"

    def test_forbidden_transition_from_completed(self):
        with pytest.raises(ValueError, match="forbidden"):
            transition_social_session_status(
                "soc_sess_1111111111111111",
                "scheduled",
                actor="admin",
                sheet_update=lambda *_: None,
                sheet_records=lambda _sid, name: (
                    self._records_with_session("completed")
                    if name == SOCIAL_SESSIONS_SHEET
                    else []
                ),
            )


class TestAuditLog:
    def test_append_audit_log_row(self):
        captured = []

        append_social_audit_log(
            "trainer",
            "session_assigned",
            "soc_app_aaaaaaaaaaaaaaaa",
            "session_id=soc_sess_x",
            sheet_append=lambda _sid, _name, values: captured.append(values),
        )

        assert len(captured) == 1
        row = dict(zip(SOCIAL_AUDIT_LOG_HEADERS, captured[0]))
        assert row["actor"] == "trainer"
        assert row["action"] == "session_assigned"
        assert row["application_id"] == "soc_app_aaaaaaaaaaaaaaaa"
        assert "session_id" in row["payload_summary"]


class TestTelegramSanitized:
    def test_session_scheduled_message_no_health(self):
        text = format_social_session_scheduled_message(
            {
                "application_id": "soc_app_test",
                "session_id": "soc_sess_test",
                "session_date": "2026-07-15",
                "session_time": "10:00",
                "location": "Зал",
                "status": "scheduled",
                "health_notes": "allergy",
                "notes": "диагноз",
            }
        )
        assert "soc_app_test" in text
        assert "soc_sess_test" in text
        assert "allergy" not in text
        assert "диагноз" not in text
        assert "status=scheduled" in text

    def test_no_magicmock_in_telegram(self):
        text = format_social_session_scheduled_message(
            {
                "application_id": MagicMock(),
                "session_id": "soc_sess_ok",
                "status": MagicMock(),
            }
        )
        assert "MagicMock" not in text
        assert "soc_sess_ok" in text

    @patch("app.services.application_notifications.send_telegram_notification", return_value=True)
    def test_notify_session_scheduled(self, mock_send):
        ok = notify_social_session_scheduled(
            {
                "application_id": "soc_app_x",
                "session_id": "soc_sess_y",
                "session_date": "2026-07-01",
                "session_time": "09:00",
                "location": "—",
                "status": "scheduled",
            }
        )
        assert ok is True
        message = mock_send.call_args[0][2]
        assert "health" not in message.lower()
        assert "MagicMock" not in message


class TestPublicApplyRegression:
    @pytest.fixture
    def social_flags_on(self, monkeypatch):
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_APPLICATIONS_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_ADMIN_NOTIFICATIONS_ENABLED", "0")
        monkeypatch.setenv("SOCIAL_BOOKING_ENABLED", "1")

    def test_social_apply_no_calendar_write(self, client, social_flags_on):
        payload = {
            "parent_name": "Иван Иванов",
            "parent_phone": "+7 916 000 00 00",
            "child_first_name": "Алексей",
            "child_age": 12,
            "preferred_contact": "phone",
            "consent_personal_data": True,
            "consent_training": True,
            "consent_version": "2026-06-v1",
        }
        with patch(
            "app.routes.social.append_social_application",
            return_value=type(
                "R",
                (),
                {"application_id": "soc_app_regtest", "status": "new"},
            )(),
        ):
            with patch("app.routes.social.notify_new_application"):
                with patch("app.routes.social.manual_assign_social_session") as mock_assign:
                    resp = client.post("/api/social/apply", json=payload)
        assert resp.status_code == 201
        mock_assign.assert_not_called()

    def test_assign_endpoint_requires_admin_token(self, client, social_flags_on, monkeypatch):
        monkeypatch.setitem(client.application.config, "ADMIN_TOKEN", "secret-token")
        resp = client.post("/api/social/sessions/assign", json=_valid_assign())
        assert resp.status_code == 401

        with patch(
            "app.routes.social.manual_assign_social_session",
            return_value=type(
                "R",
                (),
                {
                    "session_id": "soc_sess_api",
                    "application_id": "soc_app_aaaaaaaaaaaaaaaa",
                    "status": "scheduled",
                    "session_date": "2026-07-15",
                    "session_time": "10:00",
                    "location": "Зал",
                },
            )(),
        ):
            resp = client.post(
                "/api/social/sessions/assign",
                json=_valid_assign(),
                headers={"X-Admin-Token": "secret-token"},
            )
        assert resp.status_code == 201
        assert resp.get_json()["session_id"] == "soc_sess_api"


class TestBookingUnchanged:
    def test_no_booking_pipeline_imports(self):
        import ast
        import app.services.social_sessions as mod

        tree = ast.parse(open(mod.__file__, encoding="utf-8").read())
        imported = {
            node.names[0].name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert "get_available_slots" not in imported
        forbidden_modules = {
            "app.services.booking",
            "app.routes.calendar_routes",
        }
        from_modules = {
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        assert not forbidden_modules.intersection(from_modules)
