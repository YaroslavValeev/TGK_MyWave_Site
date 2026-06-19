"""MyWave Social Mission feature flags (default OFF — no production behavior change)."""

from __future__ import annotations

import os
from typing import Dict

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in _TRUTHY


def is_social_module_enabled() -> bool:
    return _env_flag("SOCIAL_MODULE_ENABLED")


def is_social_widget_enabled() -> bool:
    return is_social_module_enabled() and _env_flag("SOCIAL_WIDGET_ENABLED")


def is_social_applications_enabled() -> bool:
    return is_social_module_enabled() and _env_flag("SOCIAL_APPLICATIONS_ENABLED")


def is_social_public_stats_enabled() -> bool:
    return is_social_module_enabled() and _env_flag("SOCIAL_PUBLIC_STATS_ENABLED")


def is_social_admin_notifications_enabled() -> bool:
    return is_social_module_enabled() and _env_flag("SOCIAL_ADMIN_NOTIFICATIONS_ENABLED")


def get_social_feature_flags() -> Dict[str, bool]:
    """Snapshot for logging/tests (no secrets)."""
    return {
        "SOCIAL_MODULE_ENABLED": is_social_module_enabled(),
        "SOCIAL_WIDGET_ENABLED": is_social_widget_enabled(),
        "SOCIAL_APPLICATIONS_ENABLED": is_social_applications_enabled(),
        "SOCIAL_PUBLIC_STATS_ENABLED": is_social_public_stats_enabled(),
        "SOCIAL_ADMIN_NOTIFICATIONS_ENABLED": is_social_admin_notifications_enabled(),
    }
