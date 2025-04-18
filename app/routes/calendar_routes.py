import datetime
import sys
import logging
from flask import Blueprint, jsonify, request, current_app
from flask_socketio import emit
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.modules.booking_utils import book_slot
from app.services.google import append_to_sheet
from app.modules.sheets import get_schedule_records, get_booked_slots, get_available_slots

calendar_bp = Blueprint('calendar', __name__)
logging.basicConfig(stream=sys.stdout, level=logging.INFO, encoding="utf-8")

SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/spreadsheets'
]
CALENDAR_ID = '9e6scivqg42qmur04tbnbinm3o@group.calendar.google.com'


def get_google_services():
    credentials = service_account.Credentials.from_service_account_file(
        current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"],
        scopes=SCOPES
    )
    calendar_service = build('calendar', 'v3', credentials=credentials)
    sheets_service = build('sheets', 'v4', credentials=credentials)
    return calendar_service, sheets_service


def get_google_sheet(sheet_name):
    _, sheets_service = get_google_services()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=sheet_name
    ).execute()
    values = result.get("values", [])
    if not values:
        records = []
    else:
        headers = [h.strip().lower() for h in values[0]]
        records = [dict(zip(headers, row)) for row in values[1:]]
    class DummySheet:
        def get_all_records(self):
            return records
    return DummySheet()

def get_available_slots(check_date=None):
    import logging
    import datetime

    sheet = get_google_sheet("Schedule")
    current_date = check_date or datetime.datetime.now().strftime("%Y-%m-%d")
    day_of_week = datetime.datetime.strptime(current_date, "%Y-%m-%d").strftime("%A").lower()
    booked_slots = get_booked_slots(current_date)

    slots = []

    logging.info(f"📅 Проверяем слоты на дату: {current_date} ({day_of_week})")

    for row in sheet.get_all_records():
        row_day = row.get("day_of_week", "").strip().lower()
        if row_day != day_of_week:
            continue

        time = str(row.get("time", "")).strip()
        capacity_raw = str(row.get("max_capacity", "")).strip()  # ✅ используем max_capacity

        if not time or not capacity_raw:
            logging.warning(f"⚠️ Пустой слот или capacity в строке: {row}")
            continue

        try:
            max_capacity = int(capacity_raw)
        except ValueError:
            logging.error(f"❌ Ошибка приведения capacity к int: {capacity_raw} в {row}")
            continue

        key = f"{current_date} {time}"
        booked = booked_slots.get(key, 0)

        if booked < max_capacity:
            slots.append({
                "time": time,
                "available": max_capacity - booked,
                "max_capacity": max_capacity,
                "booked": booked
            })
            logging.info(f"✅ Добавлен слот: {key} ({booked}/{max_capacity})")
        else:
            logging.info(f"🚫 Пропуск — слот переполнен: {key} ({booked}/{max_capacity})")

    logging.info(f"✅ Найдено {len(slots)} слотов на {day_of_week}")
    return {day_of_week: slots}



def add_booking_to_calendar(date, time, name, phone):
    calendar_service, _ = get_google_services()
    try:
        start_dt = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(hours=1)
        start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%S+03:00")
        end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S+03:00")
        event = {
            'summary': f'Тренировка - {name}',
            'description': f'Клиент: {name}\nТелефон: {phone}',
            'start': {'dateTime': start_time, 'timeZone': 'Europe/Moscow'},
            'end': {'dateTime': end_time, 'timeZone': 'Europe/Moscow'}
        }
        event_result = calendar_service.events().insert(
            calendarId=CALENDAR_ID,
            body=event,
            sendNotifications=True
        ).execute()
        return True, event_result.get('htmlLink', '')
    except Exception as e:
        logging.error(f"❌ Ошибка добавления в календарь: {e}")
        return False, str(e)


@calendar_bp.route("/available_slots", methods=["GET"])
def available_slots():
    slots = get_available_slots()
    return jsonify(slots)


@calendar_bp.route("/available_slots/<date>", methods=["GET"])
def available_slots_by_date(date):
    try:
        parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d")
        if parsed_date < datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
            return jsonify([]), 200
        slots = get_available_slots(date)
        return jsonify(slots)
    except Exception as e:
        logging.error(f"❌ Ошибка получения слотов: {str(e)}")
        return jsonify([]), 200


@calendar_bp.route("/book", methods=["POST"])
def book():
    data = request.get_json()
    required_fields = ['date', 'time', 'name', 'phone']
    if not all(field in data for field in required_fields):
        return jsonify({"success": False, "error": "Все поля обязательны"}), 400

    success, result = book_slot(
        data['date'], data['time'], data['name'], data['phone']
    )

    if success:
        return jsonify({"success": True, "calendar_link": result})
    else:
        return jsonify({"success": False, "error": result}), 500

def get_slots_for_date(date):
    try:
        date_obj = datetime.datetime.strptime(date, "%Y-%m-%d")
        day_of_week = date_obj.strftime("%A").lower()

        schedule = get_schedule_records(day_of_week)
        booked = get_booked_slots(date)

        slots = []
        for entry in schedule:
            time = entry.get("time", "")
            # Безопасное получение capacity с проверкой
            capacity_raw = entry.get("capacity", "")
            # Альтернативный ключ max_capacity, если capacity не существует
            if not capacity_raw:
                capacity_raw = entry.get("max_capacity", "4")
            
            try:
                capacity = int(capacity_raw)
            except (ValueError, TypeError):
                capacity = 4  # Значение по умолчанию
                
            booked_count = booked.get(time, 0)
            available = max(0, capacity - booked_count)

            slots.append({
                "time": time,
                "available": available,
                "max_capacity": capacity,
                "booked": booked_count
            })

        return {date: slots}
    except Exception as e:
        logging.error(f"❌ Ошибка получения слотов: {e}")
        return {date: []}


@calendar_bp.route('/event', methods=['POST'])
def handle_event():
    data = request.get_json()
    date = data.get('date')

    if not date:
        return jsonify({'error': 'Дата не выбрана!'}), 400

    logging.info(f"📅 Socket.IO: Получена дата от клиента: {date}")
    slots = get_slots_for_date(date)
    emit('slots_update', {'slots': slots}, broadcast=True)
    return jsonify({"success": True})