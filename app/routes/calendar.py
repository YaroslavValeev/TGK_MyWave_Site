import datetime
from flask import Blueprint, jsonify, request, current_app
from google.oauth2 import service_account
from googleapiclient.discovery import build

calendar_bp = Blueprint('calendar', __name__)

SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/spreadsheets']

def get_google_services():
    credentials = service_account.Credentials.from_service_account_file(
        current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"],
        scopes=SCOPES
    )
    calendar_service = build('calendar', 'v3', credentials=credentials)
    sheets_service = build('sheets', 'v4', credentials=credentials)
    return calendar_service, sheets_service

# ✅ Получение доступных слотов из Google Sheets
def get_available_slots():
    _, sheets_service = get_google_services()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    range_name = "Schedule!A2:B"

    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get("values", [])

        slots = {}
        for row in values:
            if len(row) >= 2:
                day, time = row
                if day not in slots:
                    slots[day] = []
                slots[day].append(time)

        return slots

    except Exception as e:
        return {"error": f"Ошибка загрузки слотов: {str(e)}"}

@calendar_bp.route("/available_slots", methods=["GET"])
def available_slots():
    return jsonify(get_available_slots())

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
        service, _ = get_google_services()
        created_event = service.events().insert(
            calendarId="9e6scivqg42qmur04tbnbinm3o@group.calendar.google.com",
            body=event
        ).execute()
        return jsonify({'success': True, 'eventId': created_event.get('id')})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
