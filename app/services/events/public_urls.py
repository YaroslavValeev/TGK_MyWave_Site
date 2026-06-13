"""Canonical public URLs for Events-3."""

from __future__ import annotations

import os
from typing import Optional

from app.config.events_features import is_events_api_enabled, is_events_public_ui_enabled, is_events_public_ui_flag_set
from app.services.events.public_eligibility import is_public_eligible
from app.services.events.schema import NormalizedContentItem
from app.services.events.slug import build_public_slug

DEFAULT_PUBLIC_SITE_BASE_URL = "https://mywavewake.ru"


def get_public_site_base_url() -> str:
    return (os.getenv("PUBLIC_SITE_BASE_URL") or DEFAULT_PUBLIC_SITE_BASE_URL).rstrip("/")


def public_detail_path(item: NormalizedContentItem) -> Optional[str]:
    if not is_events_public_ui_flag_set() or not is_events_api_enabled():
        return None
    if not is_public_eligible(item):
        return None
    slug = build_public_slug(item)
    if not slug:
        return None
    return f"/events/{slug}"


def public_detail_url(item: NormalizedContentItem) -> Optional[str]:
    path = public_detail_path(item)
    if not path:
        return None
    return f"{get_public_site_base_url()}{path}"


def canonical_events_list_url(content_type: Optional[str] = None) -> str:
    base = get_public_site_base_url()
    if content_type:
        return f"{base}/events?type={content_type}"
    return f"{base}/events"
