from flask import Blueprint, request, render_template, url_for, make_response
import logging

booking_bp = Blueprint('booking', __name__, url_prefix='/booking')
logger = logging.getLogger(__name__)


def _success_view_content(service_type: str) -> dict:
    mapping = {
        'boat': {
            "title": "Запись на катер подтверждена!",
            "sections": [
                {
                    "h": "Что взять с собой",
                    "p": "Полотенце, вода, сменная одежда, солнцезащитный крем, отличное настроение.",
                },
                {
                    "h": "Что вас ждёт на причале",
                    "p": "Инструктаж по безопасности, знакомство с лодкой, быстрый брифинг и незабываемое время на воде.",
                },
            ],
        },
        'gym': {
            "title": "Запись на тренировку подтверждена!",
            "sections": [
                {
                    "h": "Что взять с собой",
                    "p": "Спортивная одежда, сменная обувь, полотенце, вода.",
                },
                {
                    "h": "Что вас ждёт",
                    "p": "Тренировка на баланс-бордах, отработка техники, силовые упражнения для вейксерфинга, работа над координацией.",
                },
            ],
        },
    }
    content = dict(mapping.get(service_type, mapping['boat']))
    content["next_steps"] = {
        "h": "Что дальше",
        "p": "Мы получили вашу запись. Если нужно уточнить детали — напишите или позвоните.",
        "phone": "+7 (916) 011-71-79",
        "phone_href": "tel:+79160117179",
        "telegram": "@MyW23",
        "telegram_href": "https://t.me/MyW23",
    }
    return content


@booking_bp.route('/', methods=['GET'])
def booking_form():
    """
    Отображает форму бронирования.
    Принимает тип услуги как GET-параметр для предварительного выбора
    """
    service_type = request.args.get('service', 'boat')  # По умолчанию катер
    # Используем партиалы для модальных окон
    return render_template('book.html',
                         service_type=service_type,
                         modals_partial='partials/booking_modals.html',
                         form_action=url_for('booking.book_service'))


@booking_bp.route("/success-view", methods=["GET"])
def booking_success_view():
    """Экран после записи: что взять + контакты. Без оплаты."""
    service_type = (request.args.get("type") or "boat").strip().lower()
    html = render_template("book_success.html", content=_success_view_content(service_type))
    resp = make_response(html, 200)
    resp.headers["X-Robots-Tag"] = "noindex, nofollow"
    return resp


@booking_bp.route('/book', methods=['POST'])
def book_service():
    """
    Тонкий прокси к основному API бронирования слота (`calendar.book_slot`).

    Поддерживается для обратной совместимости.
    Вся бизнес-логика бронирования живёт в /api/calendar/book.
    """
    # Импорт локально, чтобы избежать потенциальных циклических импортов
    from app.routes.calendar_routes import book_slot as calendar_book_slot
    return calendar_book_slot()
