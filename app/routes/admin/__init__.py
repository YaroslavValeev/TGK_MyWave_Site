"""
Пакет для административных маршрутов
"""

from flask import Blueprint, render_template

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/")
def index():
    """
    Главная страница административной панели
    """
    return render_template("admin/index.html")
