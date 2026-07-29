"""Feature flags for Site Admin Blog (B4)."""
from __future__ import annotations

import os
from typing import Optional

from flask import current_app, has_app_context


def _flag(name: str, default: str = "0") -> bool:
    raw: Optional[str] = None
    if has_app_context():
        try:
            raw = current_app.config.get(name)
        except Exception:
            raw = None
    if raw is None:
        raw = os.getenv(name, default)
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


def is_blog_admin_write_enabled() -> bool:
    """
    Writeback site-owned/SEO fields into raw_feed from /admin/blog.
    Default OFF — Owner enables after pull + smoke.
    """
    return _flag("BLOG_ADMIN_WRITE_ENABLED", "0")
