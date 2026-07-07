"""MyWave Online Coaching feature flags (default OFF)."""

from __future__ import annotations

import os
from typing import Dict

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in _TRUTHY


def is_online_coaching_enabled() -> bool:
    return _env_flag("ONLINE_COACHING_ENABLED")


def is_online_coaching_applications_enabled() -> bool:
    return is_online_coaching_enabled() and _env_flag("ONLINE_COACHING_APPLICATIONS_ENABLED")


def is_online_coaching_admin_enabled() -> bool:
    return is_online_coaching_enabled() and _env_flag("ONLINE_COACHING_ADMIN_ENABLED")


def is_online_coaching_notifications_enabled() -> bool:
    return is_online_coaching_enabled() and _env_flag("ONLINE_COACHING_NOTIFICATIONS_ENABLED")


def is_online_coaching_tbank_api_enabled() -> bool:
    return is_online_coaching_enabled() and _env_flag("ONLINE_COACHING_TBANK_API_ENABLED")


def is_online_coaching_reminders_enabled() -> bool:
    return is_online_coaching_enabled() and _env_flag("ONLINE_COACHING_REMINDERS_ENABLED")


def is_online_coaching_telegram_video_upload_enabled() -> bool:
    return (
        is_online_coaching_enabled()
        and is_online_coaching_applications_enabled()
        and _env_flag("ONLINE_COACHING_TELEGRAM_VIDEO_UPLOAD_ENABLED")
    )


def is_online_coaching_channel_notify_enabled() -> bool:
    return is_online_coaching_enabled() and _env_flag("ONLINE_COACHING_CHANNEL_NOTIFY_ENABLED")


def get_online_coaching_feature_flags() -> Dict[str, bool]:
    return {
        "ONLINE_COACHING_ENABLED": is_online_coaching_enabled(),
        "ONLINE_COACHING_APPLICATIONS_ENABLED": is_online_coaching_applications_enabled(),
        "ONLINE_COACHING_ADMIN_ENABLED": is_online_coaching_admin_enabled(),
        "ONLINE_COACHING_NOTIFICATIONS_ENABLED": is_online_coaching_notifications_enabled(),
        "ONLINE_COACHING_TBANK_API_ENABLED": is_online_coaching_tbank_api_enabled(),
        "ONLINE_COACHING_REMINDERS_ENABLED": is_online_coaching_reminders_enabled(),
        "ONLINE_COACHING_TELEGRAM_VIDEO_UPLOAD_ENABLED": is_online_coaching_telegram_video_upload_enabled(),
        "ONLINE_COACHING_CHANNEL_NOTIFY_ENABLED": is_online_coaching_channel_notify_enabled(),
    }
