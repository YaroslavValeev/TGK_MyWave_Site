"""
Google Sheets header contracts for MyWave Social Mission tabs.
"""

from __future__ import annotations

from typing import Iterable, List, Sequence, Tuple

SOCIAL_APPLICATIONS_SHEET = "Social_Applications"
SOCIAL_SESSIONS_SHEET = "Social_Sessions"
SOCIAL_IMPACT_SHEET = "Social_Impact"
SOCIAL_AUDIT_LOG_SHEET = "Social_Audit_Log"

SOCIAL_APPLICATIONS_HEADERS: Tuple[str, ...] = (
    "application_id",
    "created_at",
    "updated_at",
    "status",
    "parent_name",
    "parent_phone",
    "parent_email",
    "child_first_name",
    "child_age",
    "city",
    "preferred_contact",
    "telegram_username",
    "health_notes",
    "motivation_text",
    "consent_personal_data",
    "consent_training",
    "consent_media",
    "consent_version",
    "source",
    "ip_hash",
    "assigned_admin",
    "booking_id",
    "internal_notes",
)

SOCIAL_SESSIONS_HEADERS: Tuple[str, ...] = (
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
)

SOCIAL_IMPACT_HEADERS: Tuple[str, ...] = (
    "metric_key",
    "metric_value",
    "period",
    "updated_at",
)

SOCIAL_AUDIT_LOG_HEADERS: Tuple[str, ...] = (
    "event_id",
    "timestamp",
    "actor",
    "action",
    "application_id",
    "payload_summary",
)

SHEET_HEADER_CONTRACTS = {
    SOCIAL_APPLICATIONS_SHEET: SOCIAL_APPLICATIONS_HEADERS,
    SOCIAL_SESSIONS_SHEET: SOCIAL_SESSIONS_HEADERS,
    SOCIAL_IMPACT_SHEET: SOCIAL_IMPACT_HEADERS,
    SOCIAL_AUDIT_LOG_SHEET: SOCIAL_AUDIT_LOG_HEADERS,
}

APPLICATION_STATUSES = frozenset(
    {"new", "review", "approved", "rejected", "scheduled", "closed"}
)

PREFERRED_CONTACT_VALUES = frozenset({"phone", "telegram", "email"})

CHILD_AGE_MIN = 6
CHILD_AGE_MAX = 17

HEALTH_NOTES_MAX_LEN = 500

FORBIDDEN_APPLICATION_KEYS = frozenset(
    {
        "date",
        "time",
        "slot",
        "slot_id",
        "scheduled_date",
        "scheduled_time",
        "service",
        "booking_id",
        "calendar_event_id",
        "passport",
        "diagnosis",
        "disability",
        "document_scan",
    }
)


def _normalize_header(value: object) -> str:
    return str(value or "").strip().lower()


def validate_sheet_headers(
    sheet_name: str,
    headers: Sequence[str],
    *,
    required: Iterable[str] | None = None,
) -> Tuple[bool, List[str]]:
    """
    Returns (ok, missing_headers).
    Compares case-insensitively; order-independent.
    """
    contract = SHEET_HEADER_CONTRACTS.get(sheet_name)
    if contract is None:
        return False, [f"unknown_sheet:{sheet_name}"]

    expected = {_normalize_header(h) for h in (required or contract)}
    present = {_normalize_header(h) for h in headers if _normalize_header(h)}
    missing = sorted(expected - present)
    return len(missing) == 0, missing
