from flask import Blueprint, jsonify, request, render_template, url_for
import logging

booking_bp = Blueprint('booking', __name__, url_prefix='/booking')
logger = logging.getLogger(__name__)

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