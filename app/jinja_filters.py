"""Jinja2 filters for templates."""
from __future__ import annotations

from typing import Optional

from app.services.blog.display_text import plain_excerpt_for_display, plain_title_for_display


def register_jinja_filters(app) -> None:
    app.jinja_env.filters["mw_plain_title"] = plain_title_for_display
    app.jinja_env.filters["mw_plain_excerpt"] = plain_excerpt_for_display
