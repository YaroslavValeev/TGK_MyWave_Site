from flask import current_app, request, session
from flask_wtf.csrf import generate_csrf, validate_csrf as flask_validate_csrf
import logging

logger = logging.getLogger(__name__)


def get_csrf_token():
    """Получает или генерирует CSRF токен"""
    try:
        csrf_token = session.get("csrf_token")
        if not csrf_token:
            csrf_token = generate_csrf()
            session["csrf_token"] = csrf_token
        return csrf_token
    except Exception as e:
        logger.error(f"Ошибка при генерации CSRF токена: {e}")
        return None


def validate_csrf(token):
    """Проверяет CSRF токен"""
    try:
        flask_validate_csrf(token)
        return True
    except Exception as e:
        logger.warning(f"Ошибка валидации CSRF токена: {e}")
        return False


def check_csrf():
    """Проверяет CSRF токен из заголовка запроса"""
    token = None
    try:
        # Пробуем получить токен из разных источников
        token = request.headers.get("X-CSRFToken")
        if not token:
            token = request.form.get("csrf_token")
        if not token and request.is_json:
            token = request.get_json().get("csrf_token")

        if not token:
            logger.warning("CSRF токен не найден в запросе")
            return False

        return validate_csrf(token)
    except Exception as e:
        logger.error(f"Ошибка при проверке CSRF токена: {e}")
        return False
