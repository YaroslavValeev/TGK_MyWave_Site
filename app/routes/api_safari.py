"""
API endpoints для форм Wake Surf Safari 2026.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_wtf.csrf import validate_csrf, ValidationError as CSRFValidationError
from app.extensions import limiter
from app.modules.logger import get_logger
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
from datetime import datetime
from app.services.google_sheets_service import append_record
from app.services.notifications import send_telegram_notification
from app.services.projects.validation import normalize_phone, sanitize_text
from app.services.projects.analytics import get_session_data

logger = get_logger(__name__)

api_safari_bp = Blueprint("api_safari", __name__, url_prefix="/api/safari")


@api_safari_bp.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    """Обработчик ошибок rate limiting."""
    return (
        jsonify(
            {
                "success": False,
                "error": "Слишком много запросов. Пожалуйста, подождите минуту перед повторной попыткой.",
            }
        ),
        429,
    )


@api_safari_bp.route("/participant", methods=["POST"])
@limiter.limit("5 per minute", key_func=get_remote_address)
def register_participant():
    """
    API эндпоинт для регистрации участника Safari.
    Защита: rate limiting (5 запросов/минуту), CSRF, валидация.
    """
    try:
        # Проверка CSRF токена
        try:
            csrf_token = request.headers.get("X-CSRFToken") or request.form.get(
                "csrf_token"
            )
            if csrf_token:
                validate_csrf(csrf_token)
        except CSRFValidationError:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Ошибка валидации CSRF токена. Обновите страницу.",
                    }
                ),
                400,
            )

        # Получаем данные формы
        full_name = request.form.get("full_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        participation_type = request.form.get("participation_type", "").strip()
        skill_level = request.form.get("skill_level", "").strip()
        experience_years = request.form.get("experience_years", "").strip()
        city = request.form.get("city", "").strip()
        age = request.form.get("age", "").strip()
        source_info = request.form.get("source_info", "").strip()
        social_instagram = request.form.get("social_instagram", "").strip()
        social_telegram = request.form.get("social_telegram", "").strip()
        comment = request.form.get("comment", "").strip()
        consent_data = request.form.get("consent_data", "").strip() == "on"
        consent_media = request.form.get("consent_media", "").strip() == "on"

        # Базовая валидация
        if not full_name or not email or not phone:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Пожалуйста, заполните все обязательные поля.",
                    }
                ),
                400,
            )

        # Нормализуем телефон
        phone_normalized = normalize_phone(phone)

        # Собираем аналитические данные
        analytics = get_session_data()

        # Подготовка данных для сохранения
        spreadsheet_id = current_app.config.get(
            "SAFARI_SPREADSHEET_ID"
        ) or current_app.config.get("SPREADSHEET_ID")
        if not spreadsheet_id:
            logger.warning(
                "SPREADSHEET_ID не настроен, данные не будут сохранены в Sheets"
            )
        else:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sanitize_text(full_name, 100),
                phone_normalized,
                email,
                participation_type or "Не указан",
                skill_level or "Не указан",
                experience_years or "Не указано",
                sanitize_text(city, 100),
                age or "Не указан",
                source_info or "Не указан",
                sanitize_text(social_instagram, 200),
                sanitize_text(social_telegram, 200),
                sanitize_text(comment, 500),
                "Да" if consent_data else "Нет",
                "Да" if consent_media else "Нет",
                # Аналитические данные
                analytics["ip_address"],
                analytics["device_type"],
                analytics["browser"],
                analytics["referrer"],
                analytics["utm_source"],
                analytics["utm_medium"],
                analytics["utm_campaign"],
                analytics["page_url"],
            ]

            try:
                append_record(spreadsheet_id, "Safari_Leads", row)
                logger.info(f"Участник Safari зарегистрирован: {full_name} ({email})")
            except Exception as e:
                logger.error(f"Ошибка сохранения в Google Sheets: {e}")

        # Уведомление в Telegram
        try:
            notification_text = (
                f"🌊 Новая заявка участника Wake Surf Safari 2026!\n\n"
                f"👤 Имя: {full_name}\n"
                f"📱 Телефон: {phone}\n"
                f"📧 Email: {email}\n"
                f"🎯 Формат: {participation_type or 'Не указан'}\n"
                f"💬 Комментарий: {comment or 'Нет'}"
            )
            send_telegram_notification(full_name, phone, notification_text)
        except Exception as e:
            logger.warning(f"Не удалось отправить Telegram уведомление: {e}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Заявка успешно отправлена! Мы свяжемся с вами в ближайшее время.",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Ошибка при регистрации участника Safari: {e}", exc_info=True)
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Произошла ошибка при обработке запроса. Попробуйте позже.",
                }
            ),
            500,
        )


@api_safari_bp.route("/partner", methods=["POST"])
@limiter.limit("5 per minute", key_func=get_remote_address)
def register_partner():
    """API эндпоинт для регистрации партнёра Safari."""
    try:
        # Проверка CSRF
        try:
            csrf_token = request.headers.get("X-CSRFToken") or request.form.get(
                "csrf_token"
            )
            if csrf_token:
                validate_csrf(csrf_token)
        except CSRFValidationError:
            return (
                jsonify({"success": False, "error": "Ошибка валидации CSRF токена."}),
                400,
            )

        # Получаем данные
        company_name = request.form.get("company_name", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        package_interest = request.form.get("package_interest", "").strip()
        company_industry = request.form.get("company_industry", "").strip()
        company_size = request.form.get("company_size", "").strip()
        budget_range = request.form.get("budget_range", "").strip()
        previous_sponsorship = request.form.get("previous_sponsorship", "").strip()
        decision_timeline = request.form.get("decision_timeline", "").strip()
        expectations = request.form.get("expectations", "").strip()
        comment = request.form.get("comment", "").strip()

        if not company_name or not contact_name or not email or not phone:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Пожалуйста, заполните все обязательные поля.",
                    }
                ),
                400,
            )

        # Собираем аналитические данные
        analytics = get_session_data()

        # Сохранение в Sheets
        spreadsheet_id = current_app.config.get("SPREADSHEET_ID")
        if spreadsheet_id:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sanitize_text(company_name, 100),
                sanitize_text(contact_name, 100),
                normalize_phone(phone),
                email,
                package_interest or "Не указан",
                company_industry or "Не указана",
                company_size or "Не указан",
                budget_range or "Не указан",
                previous_sponsorship or "Не указан",
                decision_timeline or "Не указан",
                sanitize_text(expectations, 500),
                sanitize_text(comment, 500),
                # Аналитические данные
                analytics["ip_address"],
                analytics["device_type"],
                analytics["browser"],
                analytics["referrer"],
                analytics["utm_source"],
                analytics["utm_medium"],
                analytics["utm_campaign"],
                analytics["page_url"],
            ]
            try:
                append_record(spreadsheet_id, "Safari_Partners", row)
            except Exception as e:
                logger.error(f"Ошибка сохранения партнёра в Sheets: {e}")

        # Уведомление
        try:
            notification_text = (
                f"🤝 Новая заявка партнёра Wake Surf Safari 2026!\n\n"
                f"🏢 Компания: {company_name}\n"
                f"👤 Контакт: {contact_name}\n"
                f"📱 Телефон: {phone}\n"
                f"📧 Email: {email}\n"
                f"📦 Интерес к пакету: {package_interest or 'Не указан'}"
            )
            send_telegram_notification(contact_name, phone, notification_text)
        except Exception as e:
            logger.warning(f"Не удалось отправить Telegram уведомление: {e}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Заявка успешно отправлена! Мы свяжемся с вами для обсуждения условий партнёрства.",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Ошибка при регистрации партнёра Safari: {e}", exc_info=True)
        return (
            jsonify(
                {"success": False, "error": "Произошла ошибка при обработке запроса."}
            ),
            500,
        )


@api_safari_bp.route("/media", methods=["POST"])
@limiter.limit("5 per minute", key_func=get_remote_address)
def register_media():
    """API эндпоинт для регистрации медиа-партнёра Safari."""
    try:
        # Проверка CSRF
        try:
            csrf_token = request.headers.get("X-CSRFToken") or request.form.get(
                "csrf_token"
            )
            if csrf_token:
                validate_csrf(csrf_token)
        except CSRFValidationError:
            return (
                jsonify({"success": False, "error": "Ошибка валидации CSRF токена."}),
                400,
            )

        # Получаем данные
        media_name = request.form.get("media_name", "").strip()
        contact_name = request.form.get("contact_name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        media_type = request.form.get("media_type", "").strip()
        platform_youtube = request.form.get("platform_youtube", "").strip()
        platform_instagram = request.form.get("platform_instagram", "").strip()
        platform_tiktok = request.form.get("platform_tiktok", "").strip()
        platform_other = request.form.get("platform_other", "").strip()
        audience_total = request.form.get("audience_total", "").strip()
        audience_avg_reach = request.form.get("audience_avg_reach", "").strip()
        content_type = request.form.get("content_type", "").strip()
        audience_geo = request.form.get("audience_geo", "").strip()
        portfolio_url = request.form.get("portfolio_url", "").strip()
        collaboration_type = request.form.get("collaboration_type", "").strip()
        comment = request.form.get("comment", "").strip()

        if not media_name or not contact_name or not email or not phone:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Пожалуйста, заполните все обязательные поля.",
                    }
                ),
                400,
            )

        # Собираем аналитические данные
        analytics = get_session_data()

        # Сохранение в Sheets
        spreadsheet_id = current_app.config.get("SPREADSHEET_ID")
        if spreadsheet_id:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sanitize_text(media_name, 100),
                sanitize_text(contact_name, 100),
                normalize_phone(phone),
                email,
                media_type or "Не указан",
                platform_youtube or "0",
                platform_instagram or "0",
                platform_tiktok or "0",
                platform_other or "0",
                audience_total or "Не указано",
                audience_avg_reach or "Не указано",
                content_type or "Не указан",
                sanitize_text(audience_geo, 200),
                sanitize_text(portfolio_url, 500),
                collaboration_type or "Не указан",
                sanitize_text(comment, 500),
                # Аналитические данные
                analytics["ip_address"],
                analytics["device_type"],
                analytics["browser"],
                analytics["referrer"],
                analytics["utm_source"],
                analytics["utm_medium"],
                analytics["utm_campaign"],
                analytics["page_url"],
            ]
            try:
                append_record(spreadsheet_id, "Safari_Media", row)
            except Exception as e:
                logger.error(f"Ошибка сохранения медиа в Sheets: {e}")

        # Уведомление
        try:
            notification_text = (
                f"📸 Новая заявка медиа-партнёра Wake Surf Safari 2026!\n\n"
                f"📺 Медиа: {media_name}\n"
                f"👤 Контакт: {contact_name}\n"
                f"📱 Телефон: {phone}\n"
                f"📧 Email: {email}\n"
                f"🎯 Тип: {media_type or 'Не указан'}\n"
                f"👥 Аудитория: {audience_size or 'Не указано'}"
            )
            send_telegram_notification(contact_name, phone, notification_text)
        except Exception as e:
            logger.warning(f"Не удалось отправить Telegram уведомление: {e}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Заявка успешно отправлена! Мы свяжемся с вами для обсуждения условий сотрудничества.",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Ошибка при регистрации медиа Safari: {e}", exc_info=True)
        return (
            jsonify(
                {"success": False, "error": "Произошла ошибка при обработке запроса."}
            ),
            500,
        )


@api_safari_bp.route("/feedback", methods=["POST"])
@limiter.limit("5 per minute", key_func=get_remote_address)
def submit_feedback():
    """API эндпоинт для отправки фидбека по Safari."""
    try:
        # Проверка CSRF
        try:
            csrf_token = request.headers.get("X-CSRFToken") or request.form.get(
                "csrf_token"
            )
            if csrf_token:
                validate_csrf(csrf_token)
        except CSRFValidationError:
            return (
                jsonify({"success": False, "error": "Ошибка валидации CSRF токена."}),
                400,
            )

        # Получаем данные
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        feedback_type = request.form.get("feedback_type", "").strip()
        message = request.form.get("message", "").strip()

        if not name or not email or not message:
            return (
                jsonify(
                    {
                        "success": False,
                        "error": "Пожалуйста, заполните все обязательные поля.",
                    }
                ),
                400,
            )

        # Собираем аналитические данные
        analytics = get_session_data()

        # Сохранение в Sheets
        spreadsheet_id = current_app.config.get("SPREADSHEET_ID")
        if spreadsheet_id:
            row = [
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                sanitize_text(name, 100),
                email,
                feedback_type or "Общий",
                sanitize_text(message, 1000),
                # Аналитические данные
                analytics["ip_address"],
                analytics["device_type"],
                analytics["browser"],
                analytics["referrer"],
                analytics["utm_source"],
                analytics["utm_medium"],
                analytics["utm_campaign"],
                analytics["page_url"],
            ]
            try:
                append_record(spreadsheet_id, "Safari_Feedback", row)
            except Exception as e:
                logger.error(f"Ошибка сохранения фидбека в Sheets: {e}")

        # Уведомление
        try:
            notification_text = (
                f"💬 Новый фидбек по Wake Surf Safari 2026!\n\n"
                f"👤 Имя: {name}\n"
                f"📧 Email: {email}\n"
                f"📋 Тип: {feedback_type or 'Общий'}\n"
                f"💬 Сообщение: {message[:200]}..."
            )
            send_telegram_notification(name, email, notification_text)
        except Exception as e:
            logger.warning(f"Не удалось отправить Telegram уведомление: {e}")

        return (
            jsonify(
                {
                    "success": True,
                    "message": "Спасибо за ваш фидбек! Мы обязательно его учтём.",
                }
            ),
            200,
        )

    except Exception as e:
        logger.error(f"Ошибка при отправке фидбека Safari: {e}", exc_info=True)
        return (
            jsonify(
                {"success": False, "error": "Произошла ошибка при обработке запроса."}
            ),
            500,
        )
