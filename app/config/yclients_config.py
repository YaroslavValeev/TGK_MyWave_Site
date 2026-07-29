"""YCLIENTS feature flags and credentials (never commit secrets)."""

from __future__ import annotations

import os
from typing import List

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in _TRUTHY


def is_yclients_enabled() -> bool:
    return _flag("YCLIENTS_ENABLED", "0")


def is_yclients_read_enabled() -> bool:
    """Read slots/records when master switch is on (S5)."""
    if not is_yclients_enabled():
        return False
    return _flag("YCLIENTS_READ_ONLY_ENABLED", "1")


def is_yclients_write_enabled() -> bool:
    """Create/update/cancel only with explicit write flag (S6)."""
    if not is_yclients_enabled():
        return False
    return _flag("YCLIENTS_WRITE_ENABLED", "0")


def yclients_company_id() -> str:
    return os.environ.get("YCLIENTS_COMPANY_ID", "2043174").strip()


def yclients_api_base_url() -> str:
    return os.environ.get(
        "YCLIENTS_API_BASE_URL", "https://api.yclients.com/api/v1"
    ).strip()


def yclients_partner_token() -> str:
    return os.environ.get("YCLIENTS_PARTNER_TOKEN", "").strip()


def yclients_user_token() -> str:
    return os.environ.get("YCLIENTS_USER_TOKEN", "").strip()


def yclients_staff_id() -> str:
    return os.environ.get("YCLIENTS_STAFF_ID", "").strip()


def yclients_service_ids() -> str:
    return os.environ.get("YCLIENTS_SERVICE_IDS", "").strip()


def yclients_service_id_list() -> List[int]:
    raw = yclients_service_ids()
    if not raw:
        return []
    out: List[int] = []
    for part in raw.replace(";", ",").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            out.append(int(part))
        except ValueError:
            continue
    return out


def yclients_default_service_id() -> int | None:
    raw = os.environ.get("YCLIENTS_DEFAULT_SERVICE_ID", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    ids = yclients_service_id_list()
    return ids[0] if ids else None


def yclients_webhook_secret() -> str:
    return os.environ.get("YCLIENTS_WEBHOOK_SECRET", "").strip()


def yclients_gateway_secret() -> str:
    """Shared secret for Site/TGbotAdmin → Site internal gateway."""
    return os.environ.get("YCLIENTS_GATEWAY_SECRET", "").strip()


def yclients_slot_duration_minutes() -> int:
    """Deprecated alias: calendar slot step (30). Prefer boat_slot_duration_minutes()."""
    from app.config.booking_schedule import boat_slot_duration_minutes

    return boat_slot_duration_minutes()


def yclients_seance_minutes() -> int:
    """Ride-only minutes (default 25). Prefer yclients_slot_duration_minutes for
    journal seance_length so YC blocks 25+5 tech slot."""
    from app.config.booking_schedule import boat_seance_minutes

    return boat_seance_minutes()


def yclients_accept_header() -> str:
    return os.environ.get(
        "YCLIENTS_ACCEPT", "application/vnd.yclients.v2+json"
    ).strip()


def yclients_rate_limit_rps() -> float:
    """Partner-token soft limit (YCLIENTS: 5 rps / 200 rpm). Default 4 rps."""
    try:
        return max(0.5, float(os.environ.get("YCLIENTS_RATE_LIMIT_RPS", "4")))
    except ValueError:
        return 4.0


def is_yclients_gcal_mirror_enabled() -> bool:
    """YClients → Google Calendar mirror (default ON when YCLIENTS_ENABLED)."""
    if not is_yclients_enabled():
        return False
    return _flag("YCLIENTS_GCAL_MIRROR_ENABLED", "1")
