"""Jinja2 filters for templates."""
from __future__ import annotations

from flask import Flask

from app.services.blog.display_text import plain_excerpt_for_display, plain_title_for_display


def register_jinja_filters(app: Flask) -> None:
    """Register blog display filters on the app Jinja environment."""

    @app.template_filter("mw_plain_title")
    def _mw_plain_title(value):
        return plain_title_for_display(value)

    @app.template_filter("mw_plain_excerpt")
    def _mw_plain_excerpt(value):
        return plain_excerpt_for_display(value)

    # Дублируем в filters dict (совместимость с прямым доступом jinja_env.filters)
    app.jinja_env.filters["mw_plain_title"] = plain_title_for_display
    app.jinja_env.filters["mw_plain_excerpt"] = plain_excerpt_for_display
