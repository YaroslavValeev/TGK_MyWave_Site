import datetime
from flask import Blueprint, jsonify, request, current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build

calendar_bp = Blueprint('calendar', __name__)

SCOPES = ['https://www.googleapis.com/auth/calendar']

def get_calendar_service():
    credentials = service_account.Credentials.from_service_account_file(
        current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"],
        scopes=SCOPES
    )
    service = build('calendar', 'v3', credentials=credentials)
    return service

@calendar_bp.route("/book", methods=["POST"])
def book_training():
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Нет данных'}), 400

    date_str = data.get('date')       # Формат "YYYY-MM-DD"
    slot = data.get('slot')           # Например, "09:00"
    name = data.get('name')
    phone = data.get('phone')

    if not all([date_str, slot, name, phone]):
        return jsonify({'success': False, 'error': 'Неверные данные'}), 400

    try:
        start_dt = datetime.datetime.strptime(f"{date_str} {slot}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(hours=1)
    except Exception as e:
        return jsonify({'success': False, 'error': 'Неверный формат даты/времени'}), 400

    event = {
        'summary': f'Запись: {name}',
        'description': f'Контакт: {phone}',
        'start': {
            'dateTime': start_dt.isoformat(),
            'timeZone': 'Europe/Moscow',
        },
        'end': {
            'dateTime': end_dt.isoformat(),
            'timeZone': 'Europe/Moscow',
        },
    }

    try:
        service = get_calendar_service()
        created_event = service.events().insert(
            calendarId="9e6scivqg42qmur04tbnbinm3o@group.calendar.google.com",
            body=event
        ).execute()
        return jsonify({'success': True, 'eventId': created_event.get('id')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
