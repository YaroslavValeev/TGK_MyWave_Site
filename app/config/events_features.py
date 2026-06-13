"""Events track feature flags (default OFF)."""

from __future__ import annotations

import os
from typing import Dict

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def _env_flag(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in _TRUTHY


def is_events_classifier_enabled() -> bool:
    return _env_flag("EVENTS_CLASSIFIER_ENABLED")


def is_events_api_enabled() -> bool:
    return _env_flag("EVENTS_API_ENABLED")


def is_events_review_api_enabled() -> bool:
    return is_events_api_enabled() and _env_flag("EVENTS_REVIEW_API_ENABLED")


def get_events_feature_flags() -> Dict[str, bool]:
    return {
        "EVENTS_CLASSIFIER_ENABLED": is_events_classifier_enabled(),
        "EVENTS_API_ENABLED": is_events_api_enabled(),
        "EVENTS_REVIEW_API_ENABLED": is_events_review_api_enabled(),
    }
