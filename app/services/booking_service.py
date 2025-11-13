import logging
from datetime import datetime
from typing import Optional, Dict, Union

from sqlalchemy.exc import IntegrityError
from app.database.models import db, Booking, CalendarEvent
from app.services import google_calendar_service
from app.services import google_sheets_service

logger = logging.getLogger(__name__)


def validate_booking_data(data: dict) -> tuple[bool, Optional[str]]:
    """Validate booking data.
    Returns tuple (is_valid, error_message)
    """
    required_fields = ['name', 'phone', 'date', 'time']
    
    # Check required fields
    for field in required_fields:
        if not data.get(field):
            return False, f'missing_{field}'
    
    # Validate phone format (basic check)
    phone = data['phone'].strip()
    if not phone.replace('+', '').replace('-', '').replace(' ', '').isdigit():
        return False, 'invalid_phone'

    # Validate date format
    try:
        date = datetime.strptime(data['date'], '%Y-%m-%d')
        if date < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return False, 'date_in_past'
    except ValueError:
        return False, 'invalid_date'

    # Validate time format
    try:
        datetime.strptime(data['time'], '%H:%M')
    except ValueError:
        return False, 'invalid_time'

    return True, None


def create_booking(data: dict, user_id: Optional[int] = None) -> Dict[str, Union[bool, str, int]]:
    """Create a new booking.
    
    Args:
        data: Dict with booking details (name, phone, date, time)
        user_id: Optional user ID if booking is made by registered user
        
    Returns:
        Dict with:
            success: bool
            error: Optional error message
            booking_id: Optional ID of created booking
    """
    # Validate input
    is_valid, error = validate_booking_data(data)
    if not is_valid:
        return {'success': False, 'error': error}

    # Find or create calendar event
    calendar_event = _get_or_create_calendar_event(data['date'], data['time'])
    if not calendar_event:
        return {'success': False, 'error': 'calendar_error'}

    # Create booking record
    # Check for duplicate booking (same phone, date, time)
    try:
        existing = Booking.query.filter_by(date=data['date'], time=data['time'], phone=data['phone'].strip()).first()
        if existing:
            return {'success': False, 'error': 'duplicate_booking'}
    except Exception:
        # If DB is unavailable for check, continue and let commit handle uniqueness if enforced
        pass

    booking = Booking(
        name=data['name'].strip(),
        phone=data['phone'].strip(),
        date=data['date'],
        time=data['time'],
        user_id=user_id,
        event_id=calendar_event.id,
        status='confirmed'
    )

    try:
        db.session.add(booking)
        db.session.commit()

        # Add to Google Sheets
        _add_to_sheets(booking)

        return {
            'success': True,
            'booking_id': booking.id
        }

    except IntegrityError as e:
        db.session.rollback()
        logger.error(f"Booking creation failed: {e}")
        return {
            'success': False,
            'error': 'duplicate_booking' if 'uq_booking_date_time_phone' in str(e) else 'db_error'
        }
    except Exception as e:
        db.session.rollback()
        logger.error(f"Booking creation failed: {e}")
        return {'success': False, 'error': 'unknown_error'}


def _get_or_create_calendar_event(date: str, time: str) -> Optional[CalendarEvent]:
    """Find existing calendar event or create new one."""
    
    # First try to find existing event
    datetime_str = f"{date}T{time}:00"
    existing = CalendarEvent.query.filter_by(
        start=datetime_str
    ).first()
    
    if existing:
        return existing

    # Create new event if not found
    try:
        event = google_calendar_service.create_event(date, time)
        calendar_event = CalendarEvent.from_api(event)
        db.session.add(calendar_event)
        db.session.commit()
        return calendar_event
    except Exception as e:
        logger.error(f"Failed to create calendar event: {e}")
        return None


def _add_to_sheets(booking: Booking):
    """Add booking to Google Sheets."""
    try:
        row = [
            booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            booking.name,
            booking.phone,
            booking.date,
            booking.time,
            booking.status
        ]
        google_sheets_service.append_row(row, sheet='Bookings')
    except Exception as e:
        # Log error but don't fail booking - sheets are secondary
        logger.error(f"Failed to add booking to sheets: {e}")
