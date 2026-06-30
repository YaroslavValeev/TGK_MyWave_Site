"""
Пакет для административных маршрутов
"""
import os
from flask import Blueprint, render_template, current_app
from flask_login import login_required
from app.database.models import db, BlogPost, CalendarEvent, User, Image
from app.utils.decorators import admin_required

bp = Blueprint('admin', __name__, url_prefix='/admin')

def _safe_count(model, default=0):
    """Безопасный подсчёт записей модели."""
    try:
        return model.query.count()
    except Exception:
        return default

def _count_images_in_folder(static_folder, default=0):
    """Подсчёт файлов изображений в папке static/images."""
    try:
        images_dir = os.path.join(static_folder, 'images')
        if os.path.isdir(images_dir):
            return sum(1 for f in os.listdir(images_dir)
                       if os.path.isfile(os.path.join(images_dir, f)))
    except Exception:
        pass
    return default


def _render_section_stub(section_title: str):
    return render_template('admin/section_stub.html', section_title=section_title)


@bp.route('/')
@login_required
@admin_required
def index():
    """
    Главная страница административной панели
    """
    blog_posts_count = _safe_count(BlogPost)
    events_count = _safe_count(CalendarEvent)
    users_count = _safe_count(User)
    images_model_count = _safe_count(Image)
    images_count = images_model_count if images_model_count > 0 else _count_images_in_folder(
        current_app.static_folder
    )
    recent_actions = [
        {'icon': 'save', 'time': 'Сейчас', 'title': 'Админка', 'description': 'Панель управления загружена'},
    ]
    return render_template(
        'admin/index.html',
        blog_posts_count=blog_posts_count,
        events_count=events_count,
        images_count=images_count,
        users_count=users_count,
        recent_actions=recent_actions,
    )


@bp.route('/blog')
@login_required
@admin_required
def blog():
    return _render_section_stub('Блог')


@bp.route('/events')
@login_required
@admin_required
def events():
    return _render_section_stub('События')


@bp.route('/users')
@login_required
@admin_required
def users():
    return _render_section_stub('Пользователи')


@bp.route('/settings')
@login_required
@admin_required
def settings():
    return _render_section_stub('Настройки')
