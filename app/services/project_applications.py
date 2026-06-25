"""
Project application leads (PR54) — unified storage + Telegram notifications.

Save to Project_Applications before notify; Telegram failure must not break UX.
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, List, Mapping, Optional, Tuple

from flask import current_app

from app.modules.logger import get_logger

logger = get_logger(__name__)

PROJECT_APPLICATIONS_SHEET = "Project_Applications"
PROJECT_APPLICATIONS_HEADERS = [
    "application_id",
    "created_at",
    "updated_at",
    "status",
    "application_type",
    "name",
    "phone",
    "telegram",
    "email",
    "comment",
    "page_url",
    "source",
    "consent_version",
    "consent_personal_data",
    "consent_media",
    "notification_status",
    "notification_error",
    "utm_source",
    "utm_medium",
    "utm_campaign",
]

CONSENT_VERSION = "2026-06-v1"

_PHONE_RE = re.compile(r"\D+")
_UPDATED_RANGE_RE = re.compile(r"!A(\d+):")

ANALYTICS_EVENT_TO_APPLICATION_TYPE: dict[str, str] = {
    "ruza_lead": "ruza_camp",
    "camp_lead": "camp",
    "coach_lead": "coach_on_location",
    "consulting_lead": "consulting",
}


@dataclass(slots=True)
class ProjectApplicationResult:
    application_id: str
    status: str
    sheet_name: str
    notification_status: str
    notification_error: str


def generate_application_id() -> str:
    return f"proj_app_{uuid.uuid4().hex[:16]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "да"}


def validate_project_application(data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    name = str(data.get("name") or data.get("full_name") or data.get("parent_name") or "").strip()
    phone = str(data.get("phone") or data.get("parent_phone") or "").strip()
    telegram = str(data.get("telegram") or data.get("telegram_username") or "").strip()
    application_type = str(data.get("application_type") or "").strip()

    if len(name) < 2:
        errors.append("invalid:name")
    digits = _PHONE_RE.sub("", phone)
    email = str(data.get("email") or data.get("parent_email") or "").strip()
    if len(digits) < 10 and len(telegram) < 3 and "@" not in email:
        errors.append("invalid:contact")
    if not application_type:
        errors.append("invalid:application_type")
    return errors


def build_project_application_row(
    application_id: str,
    data: Mapping[str, Any],
    *,
    status: str = "new",
    notification_status: str = "pending",
    notification_error: str = "",
    created_at: Optional[str] = None,
    updated_at: Optional[str] = None,
) -> List[str]:
    created = created_at or _utc_now_iso()
    updated = updated_at or created
    name = str(
        data.get("name") or data.get("full_name") or data.get("parent_name") or ""
    ).strip()
    row = {
        "application_id": application_id,
        "created_at": created,
        "updated_at": updated,
        "status": status,
        "application_type": str(data.get("application_type") or "").strip(),
        "name": name,
        "phone": str(data.get("phone") or data.get("parent_phone") or "").strip(),
        "telegram": str(data.get("telegram") or data.get("telegram_username") or "").strip(),
        "email": str(data.get("email") or data.get("parent_email") or "").strip(),
        "comment": str(data.get("comment") or "").strip()[:500],
        "page_url": str(data.get("page_url") or "").strip()[:500],
        "source": str(data.get("source") or "web").strip()[:64],
        "consent_version": str(data.get("consent_version") or CONSENT_VERSION).strip(),
        "consent_personal_data": "yes" if _truthy(data.get("consent_personal_data")) else "no",
        "consent_media": "yes" if _truthy(data.get("consent_media")) else "no",
        "notification_status": notification_status,
        "notification_error": str(notification_error or "")[:200],
        "utm_source": str(data.get("utm_source") or "").strip()[:128],
        "utm_medium": str(data.get("utm_medium") or "").strip()[:128],
        "utm_campaign": str(data.get("utm_campaign") or "").strip()[:128],
    }
    return [row[h] for h in PROJECT_APPLICATIONS_HEADERS]


def resolve_spreadsheet_id() -> str:
    return (
        (current_app.config.get("SPREADSHEET_ID") if current_app else None)
        or os.getenv("SPREADSHEET_ID")
        or ""
    ).strip()


def _sheet_name() -> str:
    return (
        (current_app.config.get("PROJECT_APPLICATIONS_SHEET_NAME") if current_app else None)
        or os.getenv("PROJECT_APPLICATIONS_SHEET_NAME")
        or PROJECT_APPLICATIONS_SHEET
    )


def _parse_appended_row(updated_range: str) -> Optional[int]:
    if not updated_range:
        return None
    match = _UPDATED_RANGE_RE.search(updated_range)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


def _try_update_notification_fields(
    spreadsheet_id: str,
    sheet_name: str,
    row_number: int,
    notification_status: str,
    notification_error: str,
    *,
    sheet_update: Optional[Callable[..., Any]] = None,
) -> None:
    if not spreadsheet_id or not row_number:
        return
    updated_at = _utc_now_iso()
    try:
        updater = sheet_update
        if updater is None:
            from app.services.google_sheets_service import update_record as updater

        updater(spreadsheet_id, sheet_name, f"C{row_number}", [updated_at])
        updater(
            spreadsheet_id,
            sheet_name,
            f"P{row_number}:Q{row_number}",
            [notification_status, str(notification_error or "")[:200]],
        )
    except Exception as exc:
        logger.warning(
            "project_application_notify_status_update_failed",
            extra={"error": str(exc)[:200]},
        )


def save_project_application(
    data: Mapping[str, Any],
    *,
    application_id: Optional[str] = None,
    sheet_append: Optional[Callable[[str, str, List[str]], Any]] = None,
) -> Tuple[ProjectApplicationResult, Optional[int]]:
    """Persist application with notification_status=pending. Returns (result, sheet_row)."""
    payload = dict(data)
    if not payload.get("application_type"):
        raise ValueError("invalid:application_type")

    errors = validate_project_application(payload)
    if errors:
        raise ValueError(",".join(errors))

    app_id = application_id or generate_application_id()
    values = build_project_application_row(app_id, payload)
    sheet_name = _sheet_name()
    spreadsheet_id = resolve_spreadsheet_id()
    row_number: Optional[int] = None

    if sheet_append is not None:
        append_result = sheet_append(spreadsheet_id, sheet_name, values)
    elif spreadsheet_id:
        from app.services.google_sheets_service import append_record

        append_result = append_record(spreadsheet_id, sheet_name, values)
    else:
        logger.info(
            "project_application_saved_local_only",
            extra={"application_id": app_id, "application_type": payload.get("application_type")},
        )
        append_result = None

    if isinstance(append_result, dict):
        updated_range = append_result.get("updates", {}).get("updatedRange", "")
        row_number = _parse_appended_row(updated_range)

    logger.info(
        "project_application_saved",
        extra={
            "application_id": app_id,
            "application_type": payload.get("application_type"),
            "sheet_name": sheet_name,
        },
    )
    result = ProjectApplicationResult(
        application_id=app_id,
        status="new",
        sheet_name=sheet_name,
        notification_status="pending",
        notification_error="",
    )
    return result, row_number


def _run_notification(
    application_type: str,
    payload: Mapping[str, Any],
    application_id: str,
    *,
    notify_fn: Optional[Callable[[str, Mapping[str, Any]], bool]] = None,
) -> Tuple[str, str]:
    notify_payload = {
        **payload,
        "application_id": application_id,
        "status": "new",
    }
    if notify_fn is None:
        from app.services.application_notifications import notify_new_application

        notify_fn = notify_new_application

    try:
        ok = notify_fn(application_type, notify_payload)
        if ok:
            return "sent", ""
        return "failed_or_skipped", ""
    except Exception as exc:
        logger.warning(
            "project_application_notify_failed",
            extra={
                "application_type": application_type,
                "application_id": application_id,
                "error": str(exc)[:200],
            },
        )
        return "failed", str(exc)[:200]


def submit_project_application(
    application_type: str,
    data: Mapping[str, Any],
    *,
    sheet_append: Optional[Callable[[str, str, List[str]], Any]] = None,
    sheet_update: Optional[Callable[..., Any]] = None,
    notify_fn: Optional[Callable[[str, Mapping[str, Any]], bool]] = None,
) -> ProjectApplicationResult:
    """Save application first, then best-effort Telegram notify."""
    payload = dict(data)
    payload["application_type"] = application_type

    result, row_number = save_project_application(payload, sheet_append=sheet_append)

    notify_status, notify_error = _run_notification(
        application_type,
        payload,
        result.application_id,
        notify_fn=notify_fn,
    )

    spreadsheet_id = resolve_spreadsheet_id()
    if spreadsheet_id and row_number:
        _try_update_notification_fields(
            spreadsheet_id,
            result.sheet_name,
            row_number,
            notify_status,
            notify_error,
            sheet_update=sheet_update,
        )

    logger.info(
        "project_application_notify_result",
        extra={
            "application_id": result.application_id,
            "application_type": application_type,
            "notification_status": notify_status,
        },
    )
    return ProjectApplicationResult(
        application_id=result.application_id,
        status=result.status,
        sheet_name=result.sheet_name,
        notification_status=notify_status,
        notification_error=notify_error,
    )


def try_submit_from_analytics_event(
    event: str,
    meta: Mapping[str, Any],
    *,
    phone: str = "",
    sheet_append: Optional[Callable[[str, str, List[str]], Any]] = None,
    notify_fn: Optional[Callable[[str, Mapping[str, Any]], bool]] = None,
) -> Optional[ProjectApplicationResult]:
    """Map analytics/log events to Project_Applications + unified notify."""
    application_type = ANALYTICS_EVENT_TO_APPLICATION_TYPE.get(event)
    if not application_type:
        return None

    name = str(meta.get("name") or meta.get("parent_name") or meta.get("participant_name") or "").strip()
    phone_val = str(phone or meta.get("phone") or meta.get("parent_phone") or "").strip()
    if len(name) < 2 or len(phone_val) < 8:
        logger.warning(
            "project_application_skipped reason=missing_contact",
            extra={"application_type": application_type, "event": event},
        )
        return None

    comment_parts = [
        str(meta.get(key) or "").strip()
        for key in (
            "comment",
            "goal",
            "task",
            "topic",
            "level",
            "dates",
            "location",
            "motivation",
            "camp_date",
            "restrictions",
        )
        if str(meta.get(key) or "").strip()
    ]
    payload = {
        "name": name,
        "phone": phone_val,
        "email": str(meta.get("email") or meta.get("parent_email") or "").strip(),
        "telegram": str(meta.get("telegram") or meta.get("telegram_username") or "").strip(),
        "comment": "; ".join(comment_parts) if comment_parts else "",
        "page_url": str(meta.get("page_url") or "").strip(),
        "source": str(meta.get("service") or meta.get("source_cta") or application_type).strip(),
        "utm_source": str(meta.get("utm_source") or "").strip(),
        "utm_medium": str(meta.get("utm_medium") or "").strip(),
        "utm_campaign": str(meta.get("utm_campaign") or "").strip(),
        "consent_personal_data": meta.get("consent_personal_data", True),
        "consent_media": meta.get("consent_media", False),
    }
    try:
        return submit_project_application(
            application_type,
            payload,
            sheet_append=sheet_append,
            notify_fn=notify_fn,
        )
    except ValueError as exc:
        logger.warning(
            "project_application_validation_failed",
            extra={"application_type": application_type, "error": str(exc)[:200]},
        )
        return None
    except Exception as exc:
        logger.warning(
            "project_application_submit_failed",
            extra={"application_type": application_type, "error": str(exc)[:200]},
        )
        return None
