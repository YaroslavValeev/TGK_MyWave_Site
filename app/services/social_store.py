"""
MyWave Social Mission — data layer (Social-1).

Writes applications to Social_Applications only. No booking, no slot occupation,
no Telegram send in this module (Social-2+).
"""

from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from flask import current_app

from app.modules.logger import get_logger
from app.services.social_schema import (
    APPLICATION_STATUSES,
    CHILD_AGE_MAX,
    CHILD_AGE_MIN,
    FORBIDDEN_APPLICATION_KEYS,
    HEALTH_NOTES_MAX_LEN,
    PREFERRED_CONTACT_VALUES,
    SOCIAL_APPLICATIONS_HEADERS,
    SOCIAL_APPLICATIONS_SHEET,
    SHEET_HEADER_CONTRACTS,
    validate_sheet_headers,
)

logger = get_logger(__name__)

_APPLICATION_ID_RE = re.compile(r"^soc_app_[0-9a-f]{12,32}$", re.IGNORECASE)
_PHONE_DIGITS_RE = re.compile(r"\D+")


@dataclass(slots=True)
class SocialApplicationInput:
    parent_name: str
    parent_phone: str
    child_first_name: str
    child_age: int
    preferred_contact: str
    consent_personal_data: bool
    consent_training: bool
    consent_version: str
    parent_email: str = ""
    city: str = ""
    telegram_username: str = ""
    health_notes: str = ""
    motivation_text: str = ""
    consent_media: bool = False
    source: str = "web_social_form"
    ip_hash: str = ""


@dataclass(slots=True)
class SocialApplicationRecord:
    application_id: str
    status: str
    created_at: str
    updated_at: str
    payload: SocialApplicationInput


@dataclass(slots=True)
class SocialWriteResult:
    application_id: str
    status: str
    sheet_name: str
    row_values: List[str] = field(default_factory=list)


def generate_application_id() -> str:
    return f"soc_app_{uuid.uuid4().hex[:16]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _normalize_phone(phone: str) -> str:
    digits = _PHONE_DIGITS_RE.sub("", phone or "")
    if digits.startswith("8") and len(digits) == 11:
        digits = "7" + digits[1:]
    return digits


def _truthy_consent(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def validate_application_payload(data: Mapping[str, Any]) -> List[str]:
    """Returns list of validation errors (empty = ok)."""
    errors: List[str] = []

    for key in FORBIDDEN_APPLICATION_KEYS:
        if key in data and str(data.get(key) or "").strip():
            errors.append(f"forbidden_field:{key}")

    required_strings = {
        "parent_name": data.get("parent_name"),
        "child_first_name": data.get("child_first_name"),
        "preferred_contact": data.get("preferred_contact"),
        "consent_version": data.get("consent_version"),
    }
    for field_name, raw in required_strings.items():
        if not str(raw or "").strip():
            errors.append(f"required:{field_name}")

    if not _truthy_consent(data.get("consent_personal_data")):
        errors.append("consent_personal_data_required")
    if not _truthy_consent(data.get("consent_training")):
        errors.append("consent_training_required")

    try:
        age = int(data.get("child_age"))
    except (TypeError, ValueError):
        errors.append("invalid:child_age")
    else:
        if age < CHILD_AGE_MIN or age > CHILD_AGE_MAX:
            errors.append("invalid:child_age_range")

    preferred = str(data.get("preferred_contact") or "").strip().lower()
    if preferred and preferred not in PREFERRED_CONTACT_VALUES:
        errors.append("invalid:preferred_contact")

    phone_digits = _normalize_phone(str(data.get("parent_phone") or ""))
    telegram = str(data.get("telegram_username") or "").strip()
    if phone_digits and len(phone_digits) < 10:
        errors.append("invalid:parent_phone")

    if preferred == "telegram" and len(telegram) < 2:
        errors.append("required:telegram_username")
    elif preferred == "email":
        email_probe = str(data.get("parent_email") or "").strip()
        if not email_probe or "@" not in email_probe:
            errors.append("required:parent_email")
    elif len(phone_digits) < 10:
        errors.append("invalid:parent_phone")

    if len(phone_digits) < 10 and len(telegram) < 2:
        email_probe = str(data.get("parent_email") or "").strip()
        if "@" not in email_probe:
            errors.append("invalid:contact")

    health = str(data.get("health_notes") or "")
    if len(health) > HEALTH_NOTES_MAX_LEN:
        errors.append("invalid:health_notes_length")

    email = str(data.get("parent_email") or "").strip()
    if email and "@" not in email:
        errors.append("invalid:parent_email")

    return errors


def parse_application_input(data: Mapping[str, Any]) -> SocialApplicationInput:
    errors = validate_application_payload(data)
    if errors:
        raise ValueError("; ".join(errors))
    return SocialApplicationInput(
        parent_name=str(data["parent_name"]).strip(),
        parent_phone=str(data["parent_phone"]).strip(),
        child_first_name=str(data["child_first_name"]).strip(),
        child_age=int(data["child_age"]),
        preferred_contact=str(data["preferred_contact"]).strip().lower(),
        consent_personal_data=True,
        consent_training=True,
        consent_version=str(data["consent_version"]).strip(),
        parent_email=str(data.get("parent_email") or "").strip(),
        city=str(data.get("city") or "").strip(),
        telegram_username=str(data.get("telegram_username") or "").strip(),
        health_notes=str(data.get("health_notes") or "").strip(),
        motivation_text=str(data.get("motivation_text") or "").strip(),
        consent_media=_truthy_consent(data.get("consent_media")),
        source=str(data.get("source") or "web_social_form").strip() or "web_social_form",
        ip_hash=str(data.get("ip_hash") or "").strip(),
    )


def build_application_row(
    application_id: str,
    payload: SocialApplicationInput,
    *,
    status: str = "new",
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> Dict[str, str]:
    if status not in APPLICATION_STATUSES:
        raise ValueError(f"invalid_status:{status}")
    if not _APPLICATION_ID_RE.match(application_id):
        raise ValueError("invalid_application_id")

    ts = created_at or _utc_now_iso()
    upd = updated_at or ts
    row = {
        "application_id": application_id,
        "created_at": ts,
        "updated_at": upd,
        "status": status,
        "parent_name": payload.parent_name,
        "parent_phone": payload.parent_phone,
        "parent_email": payload.parent_email,
        "child_first_name": payload.child_first_name,
        "child_age": str(payload.child_age),
        "city": payload.city,
        "preferred_contact": payload.preferred_contact,
        "telegram_username": payload.telegram_username,
        "health_notes": payload.health_notes,
        "motivation_text": payload.motivation_text,
        "consent_personal_data": "TRUE" if payload.consent_personal_data else "FALSE",
        "consent_training": "TRUE" if payload.consent_training else "FALSE",
        "consent_media": "TRUE" if payload.consent_media else "FALSE",
        "consent_version": payload.consent_version,
        "source": payload.source,
        "ip_hash": payload.ip_hash,
        "assigned_admin": "",
        "booking_id": "",
        "internal_notes": "",
    }
    return row


def row_dict_to_values(row: Mapping[str, str]) -> List[str]:
    return [str(row.get(h, "") or "") for h in SOCIAL_APPLICATIONS_HEADERS]


def sanitize_application_for_public(record: Mapping[str, Any]) -> Dict[str, Any]:
    """Aggregated/safe view — no PII, no health details."""
    return {
        "application_id": str(record.get("application_id") or ""),
        "status": str(record.get("status") or ""),
        "child_age": record.get("child_age"),
        "city": str(record.get("city") or "") or None,
        "preferred_contact": str(record.get("preferred_contact") or ""),
        "source": str(record.get("source") or ""),
        "created_at": str(record.get("created_at") or ""),
    }


def build_admin_notification_preview(
    application_id: str,
    payload: SocialApplicationInput,
) -> str:
    """
    Telegram template contract (Social-2). No names/phones/health in message body.
    """
    city = payload.city or "—"
    return (
        "🌊 Social Mission — новая заявка\n"
        f"ID: {application_id}\n"
        "Статус: new\n"
        f"Возраст ребёнка: {payload.child_age}\n"
        f"Город: {city}\n"
        f"Контакт: {payload.preferred_contact}\n"
        "→ Sheets: Social_Applications"
    )


def resolve_social_spreadsheet_id() -> str:
    explicit = (
        (current_app.config.get("SOCIAL_SPREADSHEET_ID") if current_app else None)
        or os.getenv("SOCIAL_SPREADSHEET_ID")
        or ""
    ).strip()
    if explicit:
        return explicit
    return (
        (current_app.config.get("SPREADSHEET_ID") if current_app else None)
        or os.getenv("SPREADSHEET_ID")
        or ""
    ).strip()


def resolve_social_sheet_name(config_key: str, default: str) -> str:
    return (
        (current_app.config.get(config_key) if current_app else None)
        or os.getenv(config_key)
        or default
    ).strip()


def read_sheet_headers(
    sheet_name: str,
    *,
    spreadsheet_id: Optional[str] = None,
    header_reader: Optional[Callable[[str, str], Sequence[str]]] = None,
) -> List[str]:
    sid = spreadsheet_id or resolve_social_spreadsheet_id()
    if not sid:
        raise RuntimeError("SOCIAL_SPREADSHEET_ID/SPREADSHEET_ID is empty")

    if header_reader is not None:
        return list(header_reader(sid, sheet_name))

    from app.services.google import read_sheet

    _records, headers = read_sheet(sid, sheet_name)
    return list(headers)


def validate_social_sheet_contract(
    sheet_name: str,
    *,
    spreadsheet_id: Optional[str] = None,
    header_reader: Optional[Callable[[str, str], Sequence[str]]] = None,
) -> Tuple[bool, List[str]]:
    headers = read_sheet_headers(
        sheet_name,
        spreadsheet_id=spreadsheet_id,
        header_reader=header_reader,
    )
    return validate_sheet_headers(sheet_name, headers)


def validate_all_social_sheet_contracts(
    *,
    spreadsheet_id: Optional[str] = None,
    header_reader: Optional[Callable[[str, str], Sequence[str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    report: Dict[str, Dict[str, Any]] = {}
    for sheet_name in SHEET_HEADER_CONTRACTS:
        ok, missing = validate_social_sheet_contract(
            sheet_name,
            spreadsheet_id=spreadsheet_id,
            header_reader=header_reader,
        )
        report[sheet_name] = {"ok": ok, "missing_headers": missing}
    return report


def append_social_application(
    data: Mapping[str, Any],
    *,
    application_id: Optional[str] = None,
    status: str = "new",
    sheet_append: Optional[Callable[[str, str, List[str]], Any]] = None,
) -> SocialWriteResult:
    """
    Validate payload, build row, append to Social_Applications.
    Does not check feature flags — callers (future route) must gate externally.
    """
    payload = parse_application_input(data)
    app_id = application_id or generate_application_id()
    row_dict = build_application_row(app_id, payload, status=status)
    values = row_dict_to_values(row_dict)

    sheet_name = resolve_social_sheet_name(
        "SOCIAL_APPLICATIONS_SHEET_NAME",
        SOCIAL_APPLICATIONS_SHEET,
    )
    spreadsheet_id = resolve_social_spreadsheet_id()
    if not spreadsheet_id:
        raise RuntimeError("SOCIAL_SPREADSHEET_ID/SPREADSHEET_ID is empty")

    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)

    logger.info(
        "social_application_appended",
        extra={
            "application_id": app_id,
            "status": status,
            "sheet_name": sheet_name,
            "spreadsheet_id_tail": spreadsheet_id[-8:] if spreadsheet_id else None,
        },
    )
    return SocialWriteResult(
        application_id=app_id,
        status=status,
        sheet_name=sheet_name,
        row_values=values,
    )
