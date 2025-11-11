from flask import Blueprint, request, jsonify, session, current_app

from app.services.booking_orchestrator import orchestrate
from app.services.tools import get_available_slots


booking_api_bp = Blueprint('booking_api', __name__, url_prefix='/api')


def is_duplicate_booking(date, time, phone):
    """
    Проверяет, есть ли уже бронирование на это время/дату/номер.
    Возвращает True если дубль существует.
    """
    try:
        from app.database import db
        from app.database.models import Booking
        existing = Booking.query.filter_by(
            date=date,
            time=time,
            phone=phone
        ).first()
        return existing is not None
    except Exception as e:
        current_app.logger.warning(f"Error checking duplicate booking: {e}")
        return False


@booking_api_bp.route('/booking', methods=['POST'])
def booking_entry():
    data = request.get_json() or {}
    if data.get('reset'):
        session['booking_state'] = {}
        return jsonify(response='Состояние сброшено.', state={})

    message = data.get('message', '')
    state = data.get('state') or session.get('booking_state', {})

    current_app.logger.info(f"[booking] message='{message}' state_in={state}")
    reply_text, updated_state = orchestrate(message, state)
    current_app.logger.info(f"[booking] reply='{reply_text}' state_out={updated_state}")
    
    # Проверяем дубль, если это финальное подтверждение
    if updated_state.get('step') == 'confirm' and message.lower() in ['да', 'yes']:
        date = updated_state.get('date')
        time = updated_state.get('time')
        phone = updated_state.get('phone')
        if date and time and phone and is_duplicate_booking(date, time, phone):
            return jsonify(
                response='❌ Вы уже записаны на этот слот. Если хотите изменить, напишите нам.',
                state=updated_state,
                error='duplicate',
                status=409
            ), 409
    
    session['booking_state'] = updated_state

    # Build suggestions based on step
    suggestions = []
    step = updated_state.get('step')
    if step == 'ask_date':
        suggestions = ['сегодня', 'завтра', 'послезавтра']
    elif step == 'ask_time' and updated_state.get('date'):
        try:
            slots = get_available_slots(updated_state['date'])
            suggestions = [s.get('time') for s in (slots or [])][:6]
        except Exception:
            suggestions = []
    elif step == 'confirm':
        suggestions = ['Да', 'Нет']

    return jsonify(response=reply_text, state=updated_state, suggestions=suggestions)
