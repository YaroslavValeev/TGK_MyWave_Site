"""Feature flags for Projects / Camp section."""

from __future__ import annotations

import os
from typing import Dict

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip().lower() in _TRUTHY


def is_camp_module_enabled() -> bool:
    return _flag("CAMP_MODULE_ENABLED", "0")


def is_camp_admin_enabled() -> bool:
    return is_camp_module_enabled() and _flag("CAMP_ADMIN_ENABLED", "0")


def is_camp_public_enabled() -> bool:
    return is_camp_module_enabled() and _flag("CAMP_PUBLIC_ENABLED", "0")


def is_camp_import_enabled() -> bool:
    return is_camp_module_enabled() and _flag("CAMP_IMPORT_ENABLED", "0")


def mywave_tour_camps_feed_url() -> str:
    return os.environ.get(
        "MYWAVE_TOUR_CAMPS_FEED_URL",
        "https://api.mywavetour.ru/camps-feed.json",
    ).strip()


def mywave_tour_camps_api_url() -> str:
    return os.environ.get(
        "MYWAVE_TOUR_CAMPS_API_URL",
        "https://api.mywavetour.ru/api/v1/camps",
    ).strip()


def mywave_tour_camp_api_token() -> str:
    return os.environ.get("MYWAVE_TOUR_CAMP_API_TOKEN", "").strip()


def mywave_tour_use_api_pagination() -> bool:
    return _flag("MYWAVE_TOUR_USE_API_PAGINATION", "1")


def get_camp_feature_flags() -> Dict[str, bool]:
    return {
        "CAMP_MODULE_ENABLED": is_camp_module_enabled(),
        "CAMP_PUBLIC_ENABLED": is_camp_public_enabled(),
        "CAMP_ADMIN_ENABLED": is_camp_admin_enabled(),
        "CAMP_IMPORT_ENABLED": is_camp_import_enabled(),
        "MYWAVE_TOUR_USE_API_PAGINATION": mywave_tour_use_api_pagination(),
    }
