"""
Google Sheets header contracts for MyWave Online Coaching tabs.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Sequence, Tuple

ONLINE_REQUESTS_SHEET = "Online_Requests"
ONLINE_DIARIES_SHEET = "Online_Diaries"
ONLINE_PAYMENTS_SHEET = "Online_Payments"
ONLINE_REVIEWS_SHEET = "Online_Reviews"
ONLINE_FOLLOWUPS_SHEET = "Online_Followups"
MEDIA_FILES_SHEET = "Media_Files"

SERVICE_TYPES = frozenset({
    "video_check",
    "progress_month",
    "live_coach_land",
    "live_coach_water",
})

REQUEST_STATUSES = frozenset({
    # Video Check
    "new",
    "waiting_video",
    "video_received",
    "in_review",
    "review_ready",
    "review_sent",
    "waiting_payment",
    "paid",
    "completed",
    # Progress Month
    "subscription_active",
    "waiting_next_video",
    "diary_updated",
    "renewal_offered",
    # Live Coach
    "live_scheduled",
    "live_completed",
    # Shared / ops
    "waiting_contact",
    "followup_scheduled",
    "cancelled",
})

# Recommended statuses per product (admin UI hints; all values must be in REQUEST_STATUSES)
STATUSES_BY_SERVICE = {
    "video_check": (
        "new", "waiting_video", "video_received", "in_review", "review_ready",
        "review_sent", "waiting_payment", "paid", "completed", "cancelled",
    ),
    "progress_month": (
        "new", "waiting_payment", "paid", "subscription_active", "waiting_next_video",
        "video_received", "in_review", "diary_updated", "renewal_offered", "completed", "cancelled",
    ),
    "live_coach_land": (
        "new", "live_scheduled", "live_completed", "waiting_payment", "paid", "completed", "cancelled",
    ),
    "live_coach_water": (
        "new", "live_scheduled", "live_completed", "waiting_payment", "paid", "completed", "cancelled",
    ),
}

PAYMENT_STATUSES = frozenset({"pending", "link_sent", "paid", "failed", "refunded"})

PAYMENT_TIMINGS = frozenset({"after_service", "upfront", "package_upfront"})

PREFERRED_CHANNELS = frozenset({"telegram", "whatsapp", "max", "phone", "email"})

DISCIPLINES = frozenset({"wakesurf", "wakeboard", "both", "other"})

LEVELS = frozenset({"beginner", "intermediate", "advanced", "pro"})

SERVICE_PRICES = {
    "video_check": 1500,
    "progress_month": 12000,
    "live_coach_land": 3500,
    "live_coach_water": 3500,
}

# Billing unit for public copy, payment descriptions and Telegram notifications.
SERVICE_PRICE_UNITS = {
    "video_check": "сет",
    "progress_month": "месяц",
    "live_coach_land": "занятие",
    "live_coach_water": "занятие",
}

PROGRESS_MONTH_MAX_SESSIONS = 10

SERVICE_DISPLAY_NAMES = {
    "video_check": "Разбор видео",
    "progress_month": "Эффективный месяц",
    "live_coach_land": "Прямая связь (суша)",
    "live_coach_water": "Прямая связь (вода)",
}


def service_display_name(service_type: str) -> str:
    key = str(service_type or "").strip().lower()
    return SERVICE_DISPLAY_NAMES.get(key, key or "—")


def format_service_price(service_type: str) -> str:
    """Human-readable price with canonical billing unit (e.g. «12 000 ₽ / месяц»)."""
    key = str(service_type or "").strip().lower()
    amount = SERVICE_PRICES.get(key)
    if not amount:
        return "—"
    price_str = f"{int(amount):,}".replace(",", " ")
    unit = SERVICE_PRICE_UNITS.get(key, "")
    if key in ("live_coach_land", "live_coach_water"):
        return f"{price_str} ₽ — 60 мин"
    if unit:
        return f"{price_str} ₽ / {unit}"
    return f"{price_str} ₽"

PAYMENT_TIMING_BY_SERVICE = {
    "video_check": "after_service",
    "progress_month": "upfront",
    "live_coach_land": "after_service",
    "live_coach_water": "after_service",
}

ONLINE_REQUESTS_HEADERS: Tuple[str, ...] = (
    "online_request_id",
    "created_at",
    "updated_at",
    "client_id",
    "name",
    "phone",
    "email",
    "preferred_channel",
    "telegram_username",
    "whatsapp_phone",
    "max_contact",
    "service_type",
    "discipline",
    "level",
    "goal",
    "injuries_or_limits",
    "video_url",
    "comment",
    "payment_required_timing",
    "payment_status",
    "tbank_payment_url",
    "request_status",
    "assigned_to",
    "trainer_comment",
    "deadline_at",
    "next_followup_at",
    "diary_url",
    "source",
    "utm_source",
    "utm_medium",
    "utm_campaign",
    "consent_personal_data",
    "consent_version",
    "ip_hash",
    "review_task",
    "training_comment",
    "training_date",
    "spot_or_location",
    "in_review_at",
    "paid_at",
)

ONLINE_DIARIES_HEADERS: Tuple[str, ...] = (
    "diary_id",
    "client_id",
    "online_request_id",
    "date",
    "current_goal",
    "main_mistake",
    "water_task",
    "land_task",
    "ofp_task",
    "related_discipline_task",
    "next_video_request",
    "trainer_notes",
    "status",
    "created_at",
    "updated_at",
)

ONLINE_PAYMENTS_HEADERS: Tuple[str, ...] = (
    "payment_id",
    "online_request_id",
    "client_id",
    "amount",
    "currency",
    "service_type",
    "payment_timing",
    "tbank_order_id",
    "tbank_payment_url",
    "payment_status",
    "created_at",
    "paid_at",
    "remark",
)

MEDIA_FILES_HEADERS: Tuple[str, ...] = (
    "media_id",
    "client_id",
    "online_request_id",
    "media_type",
    "url",
    "source",
    "status",
    "created_at",
)

ONLINE_REVIEWS_HEADERS: Tuple[str, ...] = (
    "review_id",
    "online_request_id",
    "client_id",
    "rating",
    "text",
    "created_at",
    "status",
)

ONLINE_FOLLOWUPS_HEADERS: Tuple[str, ...] = (
    "followup_id",
    "online_request_id",
    "scheduled_at",
    "channel",
    "note",
    "status",
    "created_at",
)

SHEET_HEADER_CONTRACTS = {
    ONLINE_REQUESTS_SHEET: ONLINE_REQUESTS_HEADERS,
    ONLINE_DIARIES_SHEET: ONLINE_DIARIES_HEADERS,
    ONLINE_PAYMENTS_SHEET: ONLINE_PAYMENTS_HEADERS,
    ONLINE_REVIEWS_SHEET: ONLINE_REVIEWS_HEADERS,
    ONLINE_FOLLOWUPS_SHEET: ONLINE_FOLLOWUPS_HEADERS,
    MEDIA_FILES_SHEET: MEDIA_FILES_HEADERS,
}

# MVP deploy script creates/validates these tabs only (Online_Reviews — schema-only).
MVP_SHEET_CONTRACTS = {
    ONLINE_REQUESTS_SHEET: ONLINE_REQUESTS_HEADERS,
    ONLINE_DIARIES_SHEET: ONLINE_DIARIES_HEADERS,
    ONLINE_PAYMENTS_SHEET: ONLINE_PAYMENTS_HEADERS,
    ONLINE_FOLLOWUPS_SHEET: ONLINE_FOLLOWUPS_HEADERS,
    MEDIA_FILES_SHEET: MEDIA_FILES_HEADERS,
}

GOAL_MAX_LEN = 500
COMMENT_MAX_LEN = 1000
INJURIES_MAX_LEN = 500
REVIEW_TASK_MAX_LEN = 1000
TRAINING_COMMENT_MAX_LEN = 1000
TRAINING_DATE_MAX_LEN = 32
SPOT_OR_LOCATION_MAX_LEN = 200

VIDEO_URL_MAX_LEN = 500
VIDEO_URL_MAX_COUNT = 3
REVIEW_DEADLINE_HOURS = 48
VIDEO_REMINDER_HOURS = 24
IN_REVIEW_REMINDER_HOURS = 48
PAYMENT_REMINDER_HOURS = 24

_VIDEO_URL_SCHEME_RE = re.compile(r"^https?://", re.IGNORECASE)
_UNSAFE_URL_RE = re.compile(r"<[^>]+>|javascript:", re.IGNORECASE)


def normalize_video_urls(raw_urls: object) -> List[str]:
    """Normalize 1–3 video URLs from list or legacy single string."""
    urls: List[str] = []
    if isinstance(raw_urls, str):
        candidate = raw_urls.strip()
        if candidate:
            urls.append(candidate)
    elif isinstance(raw_urls, (list, tuple)):
        for item in raw_urls:
            text = str(item or "").strip()
            if text:
                urls.append(text)
    return urls[:VIDEO_URL_MAX_COUNT]


def validate_video_urls(urls: Sequence[str]) -> List[str]:
    """Return validation error codes for video URL list."""
    errors: List[str] = []
    if not urls:
        errors.append("required:video_urls")
        return errors
    if len(urls) > VIDEO_URL_MAX_COUNT:
        errors.append("invalid:video_urls_count")
    for url in urls:
        if len(url) > VIDEO_URL_MAX_LEN:
            errors.append("invalid:video_url_length")
        if not _VIDEO_URL_SCHEME_RE.match(url):
            errors.append("invalid:video_url_scheme")
        if _UNSAFE_URL_RE.search(url):
            errors.append("invalid:video_url_unsafe")
    return errors


def col_letter(index: int) -> str:
    """Convert 0-based column index to spreadsheet column letter."""
    if index < 0:
        raise ValueError("column index must be >= 0")
    result = ""
    n = index
    while True:
        result = chr(ord("A") + n % 26) + result
        n = n // 26 - 1
        if n < 0:
            break
    return result


def _normalize_header(value: object) -> str:
    return str(value or "").strip().lower()


def validate_sheet_headers(
    sheet_name: str,
    headers: Sequence[str],
    *,
    required: Iterable[str] | None = None,
) -> Tuple[bool, List[str]]:
    """Returns (ok, missing_headers). Case-insensitive; order-independent."""
    contract = SHEET_HEADER_CONTRACTS.get(sheet_name)
    if contract is None:
        return False, [f"unknown_sheet:{sheet_name}"]

    expected = {_normalize_header(h) for h in (required or contract)}
    present = {_normalize_header(h) for h in headers if _normalize_header(h)}
    missing = sorted(expected - present)
    return len(missing) == 0, missing


def payment_timing_for_service(service_type: str) -> str:
    return PAYMENT_TIMING_BY_SERVICE.get(service_type, "after_service")
