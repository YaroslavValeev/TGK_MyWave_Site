"""
Blueprint для страницы проекта Wake Surf Safari 2026.
"""

from flask import Blueprint, render_template, redirect, url_for

from app.services.project_content import load_safari_bundle

projects_safari_bp = Blueprint("projects_safari", __name__)


@projects_safari_bp.get("/projects/wakesurf-safari")
def safari_page():
    """Главная страница проекта Wake Surf Safari 2026."""
    ctx = load_safari_bundle()
    return render_template("projects/safari.html", **ctx)


@projects_safari_bp.get("/projects/wakesurf-safari-2026")
def safari_alias_2026():
    """
    Алиас для /projects/wakesurf-safari-2026.
    Пока просто рендерим ту же страницу, позже можно сделать 301 редирект.
    """
    ctx = load_safari_bundle()
    return render_template("projects/safari.html", **ctx)
