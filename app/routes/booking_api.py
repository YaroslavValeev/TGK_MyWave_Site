from flask import Blueprint, request, jsonify, session, current_app

from app.services.booking_orchestrator import orchestrate
from app.routes.calendar_routes import get_available_slots
from app.services.analytics_service import log_booking_event
from app.extensions import limiter
from app.config.rate_limit_config import RateLimitConfig
from app.services.rate_limit import limit_by_config


booking_api_bp = Blueprint('booking_api', __name__, url_prefix='/api')


def _booking_rate_limit(f):
    if limiter is None:
        return f
    return limit_by_config(limiter, RateLimitConfig.BOOKING_API, methods=["POST"])(f)


@booking_api_bp.route('/booking', methods=['POST'])
@_booking_rate_limit
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


@booking_api_bp.route('/booking/create', methods=['POST'])
def booking_create_simple():
    """Simple booking creation endpoint for forms (WakeSurfSafari frontend).
    Expects JSON: name, email, phone, startDate (YYYY-MM-DD), days, level, message
    """
    data = request.get_json() or {}
    try:
        from app.services.safari_booking_service import create_booking

        booking = create_booking(data)
        # Serialize booking object to dict
        booking_dict = {
            'id': booking.id,
            'participant_id': booking.participant_id,
            'status': booking.status,
            'start_date': booking.start_date.isoformat(),
            'days': booking.days,
            'message': booking.message,
            'route_id': booking.route_id,
            'created_at': booking.created_at.isoformat() if booking.created_at else None
        }
        # Логируем событие создания бронирования в Safari-аналитику
        try:
            log_booking_event(booking_dict, event_type='created')
        except Exception:
            current_app.logger.debug(
                'Failed to log Safari booking analytics on create',
                exc_info=True
            )
        return jsonify({'status': 'success', 'booking': booking_dict}), 201

    except ValueError as e:
        err = str(e)
        if err in ('missing_startDate', 'invalid_startDate', 'invalid_days', 'missing_email'):
            return jsonify({'status': 'error', 'error': err}), 400
        return jsonify({'status': 'error', 'error': str(e)}), 400
    except Exception as e:
        current_app.logger.exception('Error creating safari booking')
        return jsonify({'status': 'error', 'error': 'internal_error'}), 500


@booking_api_bp.route('/booking/<int:booking_id>', methods=['GET', 'PATCH'])
def booking_get_or_patch(booking_id: int):
    try:
        from app.services.safari_booking_service import get_booking, update_booking

        if request.method == 'GET':
            b = get_booking(booking_id)
            if not b:
                return jsonify({'status': 'error', 'error': 'not_found'}), 404
            booking_dict = {
                'id': b.id,
                'participant_id': b.participant_id,
                'status': b.status,
                'start_date': b.start_date.isoformat(),
                'days': b.days,
                'message': b.message,
                'route_id': b.route_id,
                'created_at': b.created_at.isoformat() if b.created_at else None
            }
            # Опционально логируем факт просмотра бронирования
            try:
                log_booking_event(booking_dict, event_type='viewed')
            except Exception:
                current_app.logger.debug(
                    'Failed to log Safari booking analytics on get',
                    exc_info=True
                )
            return jsonify({'status': 'success', 'booking': booking_dict})

        # PATCH
        data = request.get_json() or {}
        b = update_booking(booking_id, data)
        booking_dict = {
            'id': b.id,
            'participant_id': b.participant_id,
            'status': b.status,
            'start_date': b.start_date.isoformat(),
            'days': b.days,
            'message': b.message,
            'route_id': b.route_id,
            'created_at': b.created_at.isoformat() if b.created_at else None
        }
        
        # Логируем обновление/смену статуса бронирования
        try:
            log_booking_event(booking_dict, event_type='updated')
        except Exception:
            current_app.logger.debug(
                'Failed to log Safari booking analytics on patch',
                exc_info=True
            )

        return jsonify({'status': 'success', 'booking': booking_dict})

    except ValueError as e:
        err = str(e)
        if err == 'not_found':
            return jsonify({'status': 'error', 'error': err}), 404
        return jsonify({'status': 'error', 'error': err}), 400
    except Exception as e:
        current_app.logger.exception('Error handling safari booking get/patch')
        return jsonify({'status': 'error', 'error': 'internal_error'}), 500
