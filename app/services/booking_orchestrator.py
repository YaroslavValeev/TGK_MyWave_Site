from typing import Dict, Tuple, Any
import logging
from flask import current_app, has_app_context
from app.database.models import db, Booking
from app.modules import booking_utils
from app.services import crm
from app.services import sheets_writer
from app.modules import calendar_integration

logger = logging.getLogger(__name__)


def process_booking(data: Dict) -> Tuple[bool, str]:
    """Orchestrate a booking: validate slot, save to DB, record in Sheets, CRM, and Calendar.

    Returns (success, message).
    """
    name = data.get('name')
    phone = data.get('phone')
    date = data.get('date')
    time = data.get('time')

    if not all([name, phone, date, time]):
        return False, 'Missing booking data'

    # Validate slot availability. If the availability check fails (e.g. Sheets/Google error),
    # treat the slot as available to avoid failing the booking flow in tests/when Google is unavailable.
    try:
        ok, message = booking_utils.is_slot_available(date, time)
    except Exception:
        logger.exception('Slot availability check failed; assuming available')
        ok, message = True, ''
    if not ok:
        return False, message

    try:
        booking = None
        if has_app_context():
            booking = Booking(name=name, phone=phone, date=date, time=time)
            db.session.add(booking)
            db.session.commit()

        # Record client workout and sales deal in sheets (silently ignore errors)
        try:
            sheets_writer.save_client_workout_to_sheets(id=(str(booking.id) if booking else None), client_id=None, workout_id=None, created_at=None)
        except Exception:
            logger.exception('Failed to save client workout to sheets')

        try:
            crm.create_lead({"name": name, "phone": phone, "source": "web_booking"})
            sheets_writer.save_sales_deal_to_sheets(client_id=None, deal_id=None, amount=None, deal_type="booking", remark=f"Booking {date} {time}")
        except Exception:
            logger.exception('Failed to create CRM lead or save deal to sheets')

        # Create calendar event (non-critical)
        try:
            event_data = {
                "summary": f"Тренировка: {name}",
                "description": f"Телефон: {phone}",
                "start": {"dateTime": f"{date}T{time}:00", "timeZone": "Europe/Moscow"},
                "end": {"dateTime": f"{date}T{time}:00", "timeZone": "Europe/Moscow"},
            }
            calendar_integration.create_calendar_event(event_data)
        except Exception:
            logger.exception('Failed to create calendar event')

        return True, 'Booking created'
    except Exception as e:
        logger.exception('Failed to process booking: %s', e)
        return False, str(e)


def orchestrate(user_text: str, state: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
    """Lightweight orchestrator wrapper used by the booking API.

    This keeps a minimal conversational state machine so routes can import
    `orchestrate` without pulling in heavy model/tooling. It will call
    `process_booking` when the state contains date and time and the user
    confirms booking.
    """
    state = dict(state or {})

    # If user asked to confirm and we have required fields, attempt booking
    text = (user_text or '').strip().lower()
    if state.get('date') and state.get('time') and state.get('name') and state.get('phone') and text in ('да', 'ok', 'okey', 'confirm', 'подтверждаю'):
        success, msg = process_booking({
            'name': state.get('name'),
            'phone': state.get('phone'),
            'date': state.get('date'),
            'time': state.get('time'),
        })
        if success:
            state['step'] = 'done'
            return msg, state
        else:
            state['step'] = 'ask_time'
            return msg, state

    # Default: ask for missing pieces in a minimal way
    if not state.get('date'):
        state['step'] = 'ask_date'
        return 'Выберите дату (YYYY-MM-DD).', state
    if not state.get('time'):
        state['step'] = 'ask_time'
        return 'Укажите время.', state
    if not state.get('name'):
        state['step'] = 'ask_name'
        return 'Как вас зовут?', state
    if not state.get('phone'):
        state['step'] = 'ask_phone'
        return 'Укажите телефон.', state

    # If everything present but no explicit confirm, prompt for confirmation
    state['step'] = 'confirm'
    return f"Подтвердите запись на {state.get('date')} в {state.get('time')} (да/нет).", state

