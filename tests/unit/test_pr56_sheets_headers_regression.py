"""PR56/PR68 — lock Social Sheets header contracts (no drift without explicit change)."""

from app.services.social_schema import (
    SOCIAL_APPLICATIONS_HEADERS,
    SOCIAL_AUDIT_LOG_HEADERS,
    SOCIAL_SESSIONS_HEADERS,
    SHEET_HEADER_CONTRACTS,
)


def test_social_sessions_headers_count_and_order():
    expected = (
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
    )
    assert SOCIAL_SESSIONS_HEADERS == expected
    assert len(SOCIAL_SESSIONS_HEADERS) == 15


def test_social_audit_log_headers_unchanged():
    expected = (
        "event_id",
        "timestamp",
        "actor",
        "action",
        "application_id",
        "payload_summary",
    )
    assert SOCIAL_AUDIT_LOG_HEADERS == expected


def test_sheet_header_contracts_keys():
    assert set(SHEET_HEADER_CONTRACTS.keys()) == {
        "Social_Applications",
        "Social_Sessions",
        "Social_Impact",
        "Social_Audit_Log",
    }
    assert SOCIAL_APPLICATIONS_HEADERS[0] == "application_id"
