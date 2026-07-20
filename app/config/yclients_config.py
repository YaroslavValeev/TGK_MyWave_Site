"""YCLIENTS feature flags and credentials (never commit secrets)."""

from __future__ import annotations

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in _TRUTHY


def is_yclients_enabled() -> bool:
    return _flag("YCLIENTS_ENABLED", "0")


def yclients_company_id() -> str:
    return os.environ.get("YCLIENTS_COMPANY_ID", "2043174").strip()


def yclients_api_base_url() -> str:
    return os.environ.get("YCLIENTS_API_BASE_URL", "https://api.yclients.com/api/v1").strip()


def yclients_partner_token() -> str:
    return os.environ.get("YCLIENTS_PARTNER_TOKEN", "").strip()


def yclients_user_token() -> str:
    return os.environ.get("YCLIENTS_USER_TOKEN", "").strip()


def yclients_staff_id() -> str:
    return os.environ.get("YCLIENTS_STAFF_ID", "").strip()


def yclients_service_ids() -> str:
    return os.environ.get("YCLIENTS_SERVICE_IDS", "").strip()


def yclients_webhook_secret() -> str:
    return os.environ.get("YCLIENTS_WEBHOOK_SECRET", "").strip()
