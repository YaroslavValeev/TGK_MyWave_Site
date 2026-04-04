"""
Blueprint для страницы проекта WakeSurf Safari.
Флагманский премиальный experience-продукт MyWave.
"""
from flask import Blueprint, request, render_template

from app.services.project_content import load_safari_bundle
from app.services.showcases import get_showcase, load_showcase_configs

projects_safari_bp = Blueprint("projects_safari", __name__)


@projects_safari_bp.get("/projects/wakesurf-safari")
def safari_page():
    # ?nocache=1 сбрасывает кэш showcases (для проверки актуального контента после правок YAML)
    if request.args.get("nocache"):
        load_showcase_configs.cache_clear()
    ctx = load_safari_bundle()
    showcase = get_showcase("wakesurf_safari")
    ctx["showcase"] = showcase
    return render_template("projects/safari.html", **ctx)


@projects_safari_bp.get("/projects/wakesurf-safari-2026")
def safari_alias_2026():
    """Алиас для /projects/wakesurf-safari-2026."""
    ctx = load_safari_bundle()
    showcase = get_showcase("wakesurf_safari")
    ctx["showcase"] = showcase
    return render_template("projects/safari.html", **ctx)

