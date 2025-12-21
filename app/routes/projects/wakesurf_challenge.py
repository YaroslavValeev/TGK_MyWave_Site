"""
Blueprint для страницы проекта WakeSurf Challenge 2025.
"""
import json
import re
from pathlib import Path
from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for, current_app, abort
from flask_wtf.csrf import validate_csrf, ValidationError as CSRFValidationError
from app.forms.wsc2025_forms import ParticipantRegistrationForm, CoachRegistrationForm
from app.services.projects.wsc2025_service import save_participant_registration, save_coach_registration
from app.services.notifications import send_telegram_notification
from app.extensions import limiter
from app.modules.logger import get_logger
from flask_limiter.util import get_remote_address
from flask_limiter.errors import RateLimitExceeded
import markdown as md

logger = get_logger(__name__)

wakesurf_challenge_bp = Blueprint(
    'wakesurf_challenge',
    __name__,
    url_prefix='/projects',
    template_folder='../../templates'
)


@wakesurf_challenge_bp.errorhandler(RateLimitExceeded)
def handle_rate_limit(e):
    """Обработчик ошибок rate limiting."""
    return jsonify({
        "success": False,
        "error": "Слишком много запросов. Пожалуйста, подождите минуту перед повторной попыткой."
    }), 429


def _root() -> Path:
    """Возвращает корневую директорию проекта."""
    return Path(current_app.root_path).parent

def _content_dir() -> Path:
    """Возвращает путь к директории с контентом WSC2025."""
    return _root() / "content" / "projects" / "wsc2025"

def _read_text(p: Path) -> str:
    """Читает текстовый файл."""
    if not p.exists():
        logger.warning(f"Файл не найден: {p}, используем значения по умолчанию")
        return ""
    return p.read_text(encoding="utf-8")

def _read_json(p: Path, default=None):
    """Читает JSON файл."""
    if not p.exists():
        logger.warning(f"Файл не найден: {p}, используем значения по умолчанию")
        return default or {}
    try:
        return json.loads(_read_text(p))
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка парсинга JSON {p}: {e}")
        return default or {}

def _split_markdown_by_sections(md_text: str, anchors: list) -> dict:
    """
    Разбивает markdown на секции по якорям из menu.json.
    Автоматически находит заголовки и разбивает контент.
    Возвращает словарь {section_id: html_content}
    """
    if not md_text:
        return {}
    
    # Конвертируем markdown в HTML
    html = md.markdown(md_text, extensions=["extra", "sane_lists", "toc"])
    
    # Если нет якорей, возвращаем весь контент под ключом 'about'
    if not anchors:
        return {"about": html}
    
    sections = {}
    
    # Сначала находим все заголовки в HTML и создаем карту позиций
    header_pattern = r'<h([1-6])[^>]*(?:id=["\']([^"\']+)["\'])?[^>]*>(.*?)</h[1-6]>'
    headers = []
    for match in re.finditer(header_pattern, html, re.IGNORECASE | re.DOTALL):
        level = int(match.group(1))
        header_id = match.group(2) or ""
        header_text = re.sub(r'<[^>]+>', '', match.group(3)).strip()  # Убираем HTML теги из текста
        headers.append({
            'level': level,
            'id': header_id,
            'text': header_text,
            'start': match.start(),
            'end': match.end()
        })
    
    # Создаем карту якорей для быстрого поиска
    anchor_map = {a.get('id'): a.get('label', '') for a in anchors if a.get('id')}
    
    # Для каждого якоря ищем соответствующую секцию
    for section_id, section_label in anchor_map.items():
        section_html = ""
        
        # Ищем заголовок по id или по тексту
        found_header = None
        for header in headers:
            if header['id'] == section_id:
                found_header = header
                break
            elif section_label and header['text'].lower() == section_label.lower():
                found_header = header
                break
        
        if found_header:
            # Находим начало секции (после заголовка)
            start_pos = found_header['end']
            
            # Находим конец секции (следующий заголовок того же или более высокого уровня)
            end_pos = len(html)
            for header in headers:
                if header['start'] > found_header['start']:
                    if header['level'] <= found_header['level']:
                        end_pos = header['start']
                        break
            
            section_html = html[start_pos:end_pos].strip()
        
        sections[section_id] = section_html
    
    # Если не нашли ни одной секции, возвращаем весь контент под первым якорем
    if not any(sections.values()):
        first_anchor = anchors[0].get('id', 'about') if anchors else 'about'
        sections[first_anchor] = html
    
    return sections


@wakesurf_challenge_bp.route('/wakesurf-challenge-2025')
def project_page():
    """Главная страница проекта WakeSurf Challenge 2025."""
    base = _content_dir()
    
    # Читаем файлы контента
    index_md = _read_text(base / "index.md")
    meta = _read_json(base / "meta.json", {
        "title": "WakeSurf Challenge 2025 — официальный проект",
        "description": "Пилотная программа в Москве: тренировки, вебинары, прозрачное судейство (40/30/30), медиа и витрина KPI для партнёров.",
        "url": "https://mywavetraining.ru/projects/wakesurf-challenge-2025",
        "image": "https://mywavetraining.ru/static/images/challenge/challenge1.png",
        "site_name": "MyWave",
        "locale": "ru_RU"
    })
    
    menu = _read_json(base / "menu.json", {
        "anchors": [
            {"id": "about", "label": "О проекте"},
            {"id": "how", "label": "Как это работает"},
            {"id": "register", "label": "Регистрация"},
            {"id": "judging", "label": "Судейство"},
            {"id": "media", "label": "Медиа"},
            {"id": "partners", "label": "Партнёрам"},
            {"id": "final-day", "label": "Программа"},
            {"id": "webinars", "label": "Вебинары"},
            {"id": "faq", "label": "FAQ"},
            {"id": "contacts", "label": "Контакты"}
        ],
        "downloads": [
            {"label": "📄 Материалы участника", "href": "/static/docs/wsc_participant_pack.zip"},
            {"label": "📄 Материалы тренера", "href": "/static/docs/wsc_coach_pack.zip"},
            {"label": "📄 Пакет спонсора", "href": "/static/docs/wsc_sponsor_pack.zip"}
        ]
    })
    
    sponsor = _read_json(base / "sponsor_packages.json", {
        "packages": [
            {"tier": "Бронза", "price": 100000, "deliverables": ["Логотип на сайте"]},
            {"tier": "Серебро", "price": 500000, "deliverables": ["Все из Бронзы"]},
            {"tier": "Золото", "price": 1000000, "deliverables": ["Все из Серебра"]}
        ],
        "currency": "₽",
        "contacts": {"email": "Y.Valeev@gmail.com", "phone": "+7 916 011 71 79"}
    })
    
    judging = _read_json(base / "judging_criteria.json", {
        "outliers": {"threshold": 2.0}
    })
    
    schema_event = _read_json(base / "schema-event.jsonld", {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": "WakeSurf Challenge 2025"
    })
    
    # Разбиваем markdown на секции
    sections_html = _split_markdown_by_sections(index_md, menu.get("anchors", []))
    
    return render_template(
        'projects/wsc2025.html',
        project_html=index_md and md.markdown(index_md, extensions=["extra", "sane_lists"]) or "",
        sections_html=sections_html,
        meta=meta,
        menu=menu,
        sponsor=sponsor,
        judging=judging,
        schema_event=schema_event,
    )


@wakesurf_challenge_bp.route('/wakesurf-challenge-2025/api/participants/register', methods=['POST'])
@limiter.limit("5 per minute", key_func=get_remote_address)
def register_participant():
    """
    API эндпоинт для регистрации участника.
    Защита: rate limiting (5 запросов/минуту), CSRF, валидация формы.
    """
    try:
        # Проверка CSRF токена
        try:
            csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            if csrf_token:
                validate_csrf(csrf_token)
        except CSRFValidationError:
            return jsonify({
                "success": False,
                "error": "Ошибка валидации CSRF токена. Обновите страницу."
            }), 400
        
        # Валидация формы
        form = ParticipantRegistrationForm()
        if not form.validate():
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = field_errors[0] if field_errors else "Ошибка валидации"
            return jsonify({
                "success": False,
                "error": "Ошибки валидации формы",
                "errors": errors
            }), 400
        
        # Сохранение данных
        form_data = {
            'full_name': form.full_name.data,
            'birth_year': form.birth_year.data,
            'phone': form.phone.data,
            'email': form.email.data,
            'level': form.level.data,
            'city': form.city.data,
            'goals': form.goals.data or '',
            'consent_participation': form.consent_participation.data,
            'consent_media': form.consent_media.data,
        }
        
        success, error_message = save_participant_registration(form_data)
        
        if not success:
            return jsonify({
                "success": False,
                "error": error_message or "Ошибка при сохранении данных"
            }), 500
        
        # Уведомление администратору
        try:
            notification_text = (
                f"📌 Новая регистрация участника WakeSurf Challenge 2025!\n\n"
                f"👤 Имя: {form_data['full_name']}\n"
                f"📱 Телефон: {form_data['phone']}\n"
                f"📧 Email: {form_data['email']}\n"
                f"🎯 Уровень: {form_data['level']}\n"
                f"📍 Город: {form_data['city']}"
            )
            send_telegram_notification(
                form_data['full_name'],
                form_data['phone'],
                notification_text
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить Telegram уведомление: {e}")
        
        return jsonify({
            "success": True,
            "message": "Регистрация успешно завершена! Мы свяжемся с вами в ближайшее время."
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации участника: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Произошла ошибка при обработке запроса. Попробуйте позже."
        }), 500


@wakesurf_challenge_bp.route('/wakesurf-challenge-2025/api/coaches/register', methods=['POST'])
@limiter.limit("5 per minute", key_func=get_remote_address)
def register_coach():
    """
    API эндпоинт для регистрации тренера.
    Защита: rate limiting (5 запросов/минуту), CSRF, валидация формы.
    """
    try:
        # Проверка CSRF токена
        try:
            csrf_token = request.headers.get('X-CSRFToken') or request.form.get('csrf_token')
            if csrf_token:
                validate_csrf(csrf_token)
        except CSRFValidationError:
            return jsonify({
                "success": False,
                "error": "Ошибка валидации CSRF токена. Обновите страницу."
            }), 400
        
        # Валидация формы
        form = CoachRegistrationForm()
        if not form.validate():
            errors = {}
            for field, field_errors in form.errors.items():
                errors[field] = field_errors[0] if field_errors else "Ошибка валидации"
            return jsonify({
                "success": False,
                "error": "Ошибки валидации формы",
                "errors": errors
            }), 400
        
        # Сохранение данных
        form_data = {
            'full_name': form.full_name.data,
            'phone': form.phone.data,
            'email': form.email.data,
            'club': form.club.data or '',
            'experience_years': form.experience_years.data,
            'portfolio_url': form.portfolio_url.data or '',
            'consent_participation': form.consent_participation.data,
            'consent_media': form.consent_media.data,
        }
        
        success, error_message = save_coach_registration(form_data)
        
        if not success:
            return jsonify({
                "success": False,
                "error": error_message or "Ошибка при сохранении данных"
            }), 500
        
        # Уведомление администратору
        try:
            notification_text = (
                f"📌 Новая регистрация тренера WakeSurf Challenge 2025!\n\n"
                f"👤 Имя: {form_data['full_name']}\n"
                f"📱 Телефон: {form_data['phone']}\n"
                f"📧 Email: {form_data['email']}\n"
                f"🏆 Опыт: {form_data['experience_years']} лет\n"
                f"🏢 Клуб: {form_data['club'] or 'Не указан'}"
            )
            send_telegram_notification(
                form_data['full_name'],
                form_data['phone'],
                notification_text
            )
        except Exception as e:
            logger.warning(f"Не удалось отправить Telegram уведомление: {e}")
        
        return jsonify({
            "success": True,
            "message": "Регистрация успешно завершена! Мы свяжемся с вами в ближайшее время."
        }), 200
        
    except Exception as e:
        logger.error(f"Ошибка при регистрации тренера: {e}", exc_info=True)
        return jsonify({
            "success": False,
            "error": "Произошла ошибка при обработке запроса. Попробуйте позже."
        }), 500

