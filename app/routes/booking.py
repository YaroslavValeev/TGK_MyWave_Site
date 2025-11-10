from flask import Blueprint, jsonify, request, render_template, url_for
from app.extensions import csrf
from app.services.booking_service import create_booking
from flask_login import current_user
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
    Обрабатывает отправку формы бронирования
    """
    try:
        data = request.get_json()
        
        # Получаем user_id из сессии если пользователь авторизован
        user_id = current_user.id if not current_user.is_anonymous else None

        result = create_booking(
            data={
                'name': data['name'],
                'phone': data['phone'],
                'date': data['date'],
                'time': data['time'],
                'service_id': data.get('service', 'boat')  # По умолчанию катер
            },
            user_id=user_id
        )

        if result['success']:
            return jsonify({
                "status": "success",
                "message": "Бронирование успешно создано",
                "booking_id": result['booking_id'],
                "success_view_url": url_for('booking.booking_success_view', 
                                          type=data.get('service', 'boat'))
            })
        else:
            error = result.get('error', 'unknown_error')
            if error in ['invalid_date', 'invalid_time', 'date_in_past', 
                        'invalid_phone', 'duplicate_booking']:
                return jsonify({
                    "status": "error",
                    "error": error
                }), 400
            else:
                logger.error(f"Ошибка при бронировании: {error}")
                return jsonify({
                    "status": "error", 
                    "error": "Произошла внутренняя ошибка сервера"
                }), 500
            
    except Exception as e:
        logger.error(f"Ошибка при обработке запроса бронирования: {e}", 
                    exc_info=True)
        return jsonify({
            "status": "error",
            "error": str(e)
        }), 500