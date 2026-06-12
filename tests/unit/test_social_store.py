"""Social Mission data layer (Social-1)."""

import re

import pytest

from app.services.social_schema import (
    SOCIAL_APPLICATIONS_HEADERS,
    SOCIAL_APPLICATIONS_SHEET,
    SOCIAL_AUDIT_LOG_SHEET,
    SOCIAL_IMPACT_SHEET,
    SOCIAL_SESSIONS_SHEET,
    validate_sheet_headers,
)
from app.services.social_store import (
    append_social_application,
    build_admin_notification_preview,
    build_application_row,
    generate_application_id,
    parse_application_input,
    row_dict_to_values,
    sanitize_application_for_public,
    validate_all_social_sheet_contracts,
    validate_application_payload,
)


def _valid_payload(**overrides):
    base = {
        "parent_name": "Иван Иванов",
        "parent_phone": "+7 916 000 00 00",
        "child_first_name": "Алексей",
        "child_age": 12,
        "preferred_contact": "phone",
        "consent_personal_data": True,
        "consent_training": True,
        "consent_version": "2026-06-v1",
        "city": "Москва",
        "health_notes": "Нужен спасжилет",
    }
    base.update(overrides)
    return base


class TestApplicationId:
    def test_generate_application_id_format(self):
        app_id = generate_application_id()
        assert re.match(r"^soc_app_[0-9a-f]{16}$", app_id)

    def test_generate_application_id_unique(self):
        ids = {generate_application_id() for _ in range(20)}
        assert len(ids) == 20


class TestValidation:
    def test_required_fields(self):
        errors = validate_application_payload({})
        assert "required:parent_name" in errors
        assert "required:parent_phone" in errors
        assert "required:child_first_name" in errors
        assert "consent_personal_data_required" in errors
        assert "consent_training_required" in errors

    def test_consent_must_be_true(self):
        errors = validate_application_payload(
            _valid_payload(consent_personal_data=False, consent_training=False)
        )
        assert "consent_personal_data_required" in errors
        assert "consent_training_required" in errors

    def test_child_age_range(self):
        errors = validate_application_payload(_valid_payload(child_age=5))
        assert "invalid:child_age_range" in errors
        errors = validate_application_payload(_valid_payload(child_age=18))
        assert "invalid:child_age_range" in errors

    def test_forbidden_slot_fields(self):
        errors = validate_application_payload(
            _valid_payload(date="2026-07-01", slot="10:00")
        )
        assert "forbidden_field:date" in errors
        assert "forbidden_field:slot" in errors

    def test_health_notes_max_length(self):
        errors = validate_application_payload(
            _valid_payload(health_notes="x" * 501)
        )
        assert "invalid:health_notes_length" in errors


class TestWritePayload:
    def test_build_row_matches_headers_order(self):
        payload = parse_application_input(_valid_payload())
        app_id = generate_application_id()
        row_dict = build_application_row(app_id, payload, status="new")
        values = row_dict_to_values(row_dict)

        assert len(values) == len(SOCIAL_APPLICATIONS_HEADERS)
        assert values[0] == app_id
        assert values[3] == "new"
        assert values[SOCIAL_APPLICATIONS_HEADERS.index("parent_name")] == "Иван Иванов"
        assert values[SOCIAL_APPLICATIONS_HEADERS.index("booking_id")] == ""

    def test_append_uses_injected_writer(self):
        captured = {}

        def fake_append(spreadsheet_id, sheet_name, values):
            captured["spreadsheet_id"] = spreadsheet_id
            captured["sheet_name"] = sheet_name
            captured["values"] = values

        result = append_social_application(
            _valid_payload(),
            sheet_append=fake_append,
        )

        assert result.status == "new"
        assert result.sheet_name == SOCIAL_APPLICATIONS_SHEET
        assert captured["sheet_name"] == SOCIAL_APPLICATIONS_SHEET
        assert captured["values"][3] == "new"
        assert result.application_id.startswith("soc_app_")


class TestPrivacy:
    def test_public_sanitize_excludes_pii_and_health(self):
        safe = sanitize_application_for_public(
            {
                "application_id": "soc_app_abc",
                "status": "new",
                "parent_name": "Secret",
                "parent_phone": "+7999",
                "child_first_name": "Child",
                "health_notes": "allergy",
                "child_age": 10,
                "city": "Москва",
                "preferred_contact": "phone",
                "source": "web_social_form",
                "created_at": "2026-06-12T00:00:00Z",
            }
        )
        assert "parent_name" not in safe
        assert "parent_phone" not in safe
        assert "child_first_name" not in safe
        assert "health_notes" not in safe
        assert safe["application_id"] == "soc_app_abc"
        assert safe["child_age"] == 10

    def test_admin_notification_preview_no_pii(self):
        payload = parse_application_input(_valid_payload())
        text = build_admin_notification_preview("soc_app_test123", payload)
        assert "Иван" not in text
        assert "+7" not in text
        assert "спасжилет" not in text
        assert "soc_app_test123" in text
        assert "12" in text


class TestSheetHeadersContract:
    def test_applications_headers_validation_ok(self):
        ok, missing = validate_sheet_headers(
            SOCIAL_APPLICATIONS_SHEET,
            list(SOCIAL_APPLICATIONS_HEADERS),
        )
        assert ok is True
        assert missing == []

    def test_applications_headers_validation_missing(self):
        ok, missing = validate_sheet_headers(
            SOCIAL_APPLICATIONS_SHEET,
            ["application_id", "status"],
        )
        assert ok is False
        assert "parent_phone" in missing

    def test_validate_all_contracts_with_reader(self):
        def reader(_sid, sheet_name):
            return list(
                {
                    SOCIAL_APPLICATIONS_SHEET: SOCIAL_APPLICATIONS_HEADERS,
                    SOCIAL_SESSIONS_SHEET: (
                        "session_id",
                        "application_id",
                        "scheduled_date",
                        "scheduled_time",
                        "service",
                        "booking_id",
                        "calendar_event_id",
                        "status",
                        "created_at",
                        "created_by",
                    ),
                    SOCIAL_IMPACT_SHEET: (
                        "metric_key",
                        "metric_value",
                        "period",
                        "updated_at",
                    ),
                    SOCIAL_AUDIT_LOG_SHEET: (
                        "event_id",
                        "timestamp",
                        "actor",
                        "action",
                        "application_id",
                        "payload_summary",
                    ),
                }[sheet_name]
            )

        report = validate_all_social_sheet_contracts(header_reader=reader)
        assert all(item["ok"] for item in report.values())
