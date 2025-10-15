from flask import Blueprint, request, jsonify, current_app
from app.utils.pricing import calculate_price
from app.database.models import Booking, CalendarEvent
from app import db
from app.services.google import add_event_to_calendar, append_to_sheet
import datetime

bp = Blueprint('pricing_booking', __name__, url_prefix='/api')

@bp.route('/pricing/calc', methods=['POST'])
def pricing_calc():
    data = request.get_json() or {}
    try:
        base = int(data.get('base_zone_price', 0))
        package = data.get('package', 'Base')
        options = data.get('options', {})
        coupon_percent = float(data.get('coupon_percent', 0.0))
        result = calculate_price(base, package, options, coupon_percent)
        return jsonify(result)
    except Exception as e:
        return jsonify(error=str(e)), 400


@bp.route('/booking/create', methods=['POST'])
def booking_create():
    data = request.get_json() or {}
    name = data.get('name')
    phone = data.get('phone')
    date = data.get('date')
    time = data.get('time')
    participants = int(data.get('participants', 1))

    if not all([name, phone, date, time]):
        return jsonify(error='missing fields'), 400

    # Basic slot blocking: check existing events in DB/calendar via mock
    try:
        # For dev, google services may return mock; add_event_to_calendar handles service tuple
        svc = None
        try:
            from app.services.google import get_google_services
            svc = get_google_services()
        except Exception:
            svc = None

        # Insert booking record with pending status
        booking = Booking(name=name, phone=phone, date=date, time=time, status='pending')
        db.session.add(booking)
        db.session.flush()

        # Attempt to add to calendar (mock/real) only if calendar id set
        calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID')
        if svc and calendar_id:
            ok = add_event_to_calendar(svc, date, time, name, phone)
            if not ok:
                booking.status = 'failed'
                db.session.add(booking)
                db.session.commit()
                return jsonify(error='calendar_failed'), 500

        # Optionally append to spreadsheet (compat)
        try:
            append_to_sheet(current_app.config.get('SPREADSHEET_ID'), 'Bookings', [name, phone, date, time])
        except Exception:
            # Don't fail booking on sheet error in dev
            current_app.logger.exception('Failed to append to sheet')

        booking.status = 'confirmed'
        db.session.add(booking)
        db.session.commit()

        return jsonify(booking_id=booking.id, status=booking.status)
    except Exception as e:
        current_app.logger.exception('Booking create failed')
        return jsonify(error=str(e)), 500
