from flask import Blueprint, request, jsonify, session, current_app

from app.services.booking_orchestrator import orchestrate
from app.services.tools import get_available_slots


booking_api_bp = Blueprint('booking_api', __name__, url_prefix='/api')


@booking_api_bp.route('/booking', methods=['POST'])
def booking_entry():
    data = request.get_json() or {}
    if data.get('reset'):
        session['booking_state'] = {}
        return jsonify(response='Состояние сброшено.', state={})

    message = data.get('message', '')
    state = data.get('state') or session.get('booking_state', {})

    current_app.logger.info(f"[booking] message='{message}' state_in={state}")
    try:
        reply_text, updated_state = orchestrate(message, state)
        current_app.logger.info(f"[booking] reply='{reply_text}' state_out={updated_state}")
        session['booking_state'] = updated_state
    except Exception as exc:
        current_app.logger.error("[booking] orchestrate failed: %s", exc, exc_info=True)
        # Keep API contract stable for the frontend/chat widget: return a response string with 200.
        return jsonify(
            response="Сервис записи временно недоступен. Попробуйте чуть позже.",
            state=state,
            suggestions=[],
        ), 200

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
