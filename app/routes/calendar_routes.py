import datetime
import sys
import logging
from flask import Blueprint, jsonify, request, current_app
from flask_socketio import emit
from google.oauth2 import service_account
from googleapiclient.discovery import build
from app.services.google import append_to_sheet  # добавлено для сохранения брони в Client_Workouts

calendar_bp = Blueprint('calendar', __name__)
# Настраиваем логирование с кодировкой UTF-8
logging.basicConfig(stream=sys.stdout, level=logging.INFO, encoding="utf-8")

SCOPES = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/spreadsheets']
CALENDAR_ID = '9e6scivqg42qmur04tbnbinm3o@group.calendar.google.com'

def get_google_services():
    credentials = service_account.Credentials.from_service_account_file(
        current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"],
        scopes=SCOPES
    )
    calendar_service = build('calendar', 'v3', credentials=credentials)
    sheets_service = build('sheets', 'v4', credentials=credentials)
    return calendar_service, sheets_service

# ✅ Получение забронированных мест
def get_booked_slots():
    _, sheets_service = get_google_services()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    range_name = "Client_Workouts!A2:E"  # изменено: расширен диапазон для получения всех столбцов

    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get("values", [])
        
        booked_slots = {}
        for row in values:
            if len(row) >= 3:
                date = row[1]  # Changed from row[0] to row[1]
                time = row[2]  # Changed from row[1] to row[2]
                key = f"{date} {time}"
                booked_slots[key] = booked_slots.get(key, 0) + 1

        return booked_slots
    except Exception as e:
        logging.error(f"❌ Error accessing Client_Workouts: {str(e)}")
        return {}

# ✅ Получение доступных слотов
def get_available_slots(check_date=None):
    _, sheets_service = get_google_services()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]

    workouts_result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Schedule!A2:C"
    ).execute()
    workouts = workouts_result.get("values", [])

    booked_slots = get_booked_slots()
    slots = {}
    current_date = check_date or datetime.datetime.now().strftime("%Y-%m-%d")
    day_of_week = datetime.datetime.strptime(current_date, "%Y-%m-%d").strftime("%A").lower()

    for workout in workouts:
        if workout[0].strip().lower() == day_of_week:
            slot_key = f"{current_date} {workout[1]}"
            capacity = int(workout[2])
            booked = booked_slots.get(slot_key, 0)
            if day_of_week not in slots:
                slots[day_of_week] = []
            slots[day_of_week].append({
                "time": workout[1],
                "available": capacity - booked,
                "max_capacity": capacity,
                "booked": booked
            })
    # Удаляем заполненные слоты
    for slot in slots.get(day_of_week, [])[:]:  # копия списка через [:] чтобы удаление было безопасным
        key = f"{current_date} {slot['time']}"
        if booked_slots.get(key, 0) >= slot["max_capacity"]:
            slots[day_of_week].remove(slot)
    return slots

def add_booking_to_calendar(date, time, name, phone):
    calendar_service, _ = get_google_services()
    
    logging.info(f"📅 Создание события: дата={date}, время={time}, имя={name}")
    
    try:
        # Parse date and time separately for better clarity
        start_dt = datetime.datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        end_dt = start_dt + datetime.timedelta(hours=1)
        
        # Format time properly for Google Calendar API
        start_time = start_dt.strftime("%Y-%m-%dT%H:%M:%S+03:00")
        end_time = end_dt.strftime("%Y-%m-%dT%H:%M:%S+03:00")
        
        event = {
            'summary': f'Тренировка - {name}',
            'description': f'Клиент: {name}\nТелефон: {phone}',
            'start': {
                'dateTime': start_time,
                'timeZone': 'Europe/Moscow'
            },
            'end': {
                'dateTime': end_time,
                'timeZone': 'Europe/Moscow'
            }
        }

        event_result = calendar_service.events().insert(
            calendarId=CALENDAR_ID, 
            body=event,
            sendNotifications=True
        ).execute()
        
        if 'id' in event_result:
            logging.info(f"✅ Событие успешно добавлено в календарь: ID={event_result['id']}")
            return True, event_result.get('htmlLink')
        else:
            logging.error("❌ Событие создано, но без ID")
            return False, "Ошибка создания события"
            
    except Exception as e:
        logging.error(f"❌ Ошибка добавления в Google Calendar: {e}")
        return False, str(e)

@calendar_bp.route("/available_slots", methods=["GET"])
def available_slots():
    slots = get_available_slots()
    print(f"📅 Отправляем на клиент слоты: {slots}")
    return jsonify(slots)

@calendar_bp.route("/available_slots/<date>", methods=["GET"])
def available_slots_by_date(date):
    try:
        logging.info(f"📅 Получен запрос слотов на дату: {date}")
        
        # Strict date format validation
        try:
            parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d")
            if parsed_date < datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
                raise ValueError("Date cannot be in the past")
        except ValueError as e:
            logging.error(f"❌ Ошибка валидации даты: {str(e)}")
            return jsonify({
                "error": "Invalid date format or past date. Use YYYY-MM-DD and future dates only"
            }), 400

        slots = get_available_slots(date)
        logging.info(f"📊 Найдено слотов: {len(slots)}")
        print(f"📅 Отправляем на клиент слоты: {slots}")
        return jsonify(slots)
    except Exception as e:
        logging.error(f"❌ Ошибка при получении слотов: {str(e)}")
        return jsonify({"error": str(e)}), 500

@calendar_bp.route("/book", methods=["POST"])
def book():
    try:
        data = request.get_json()
        logging.info(f"📥 Запрос на запись: {data}")

        if not all(key in data for key in ['date', 'time', 'name', 'phone']):
            return jsonify({"success": False, "error": "All fields are required"}), 400

        date = data['date']
        time = data['time']
        name = data['name']
        phone = data['phone']
        source = "web"

        created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        _, sheets_service = get_google_services()
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        
        # Проверяем существование клиента
        clients_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Clients!A2:H"
        ).execute()

        client_id = None
        if "values" in clients_result:
            for row in clients_result["values"]:
                if len(row) >= 3 and (row[2] == name or row[3] == phone):
                    client_id = row[0]
                    break

        if not client_id:
            client_id = f"client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"
            new_client = [[client_id, "", name, phone, "", "beginner", created_at, source, created_at]]
            append_to_sheet(sheets_service, spreadsheet_id, "Clients!A2:H", new_client)

        # Формируем корректный workout_id
        workout_id = f"workout_{date}_{time.replace(':', '')}" if date and time else None
        if workout_id is None:
            return jsonify({"success": False, "error": "Некорректные данные"}), 400

        # Проверяем существующую тренировку
        workouts_result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Workouts!A2:J"
        ).execute()

        workout_found = False
        current_capacity = 0
        if "values" in workouts_result:
            for row in workouts_result["values"]:
                if len(row) >= 3 and row[1] == date and row[2] == time:
                    workout_id = row[0]
                    current_capacity = int(row[9]) if len(row) > 9 and row[9].isdigit() else 0
                    workout_found = True
                    break

        # Запись в Client_Workouts
        new_booking = [[
            f"cw-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}",
            client_id,
            workout_id,
            "",
            "",
            "single",
            "подтверждено",
            created_at,
            ""
        ]]
        append_to_sheet(sheets_service, spreadsheet_id, "Client_Workouts!A2:I", new_booking)

        # Обновляем или создаем тренировку
        if workout_found:
            update_range = f"Workouts!J{workouts_result['values'].index(row) + 2}"
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=update_range,
                valueInputOption="RAW",
                body={"values": [[str(current_capacity + 1)]]}
            ).execute()
        else:
            new_workout = [[
                workout_id, date, time, "60", "зал", "групповая", "Тренер", "активно", "1", created_at
            ]]
            append_to_sheet(sheets_service, spreadsheet_id, "Workouts!A2:J", new_workout)

        return jsonify({"success": True, "message": "Запись подтверждена!"})

    except Exception as e:
        logging.error(f"❌ Ошибка записи на тренировку: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

def get_slots_for_date(date):
    """Wrapper function for get_available_slots to handle socket.io requests"""
    try:
        logging.info(f"📅 Socket.IO: Получен запрос слотов на дату: {date}")
        
        # Validate date format
        try:
            parsed_date = datetime.datetime.strptime(date, "%Y-%m-%d")
            if (parsed_date < datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)):
                return {"error": "Date cannot be in the past"}
        except ValueError as e:
            logging.error(f"❌ Socket.IO: Ошибка валидации даты: {str(e)}")
            return {"error": "Invalid date format. Use YYYY-MM-DD"}

        slots = get_available_slots(date)
        logging.info(f"📊 Socket.IO: Найдено слотов: {len(slots)}")
        return slots
    except Exception as e:
        logging.error(f"❌ Socket.IO: Ошибка при получении слотов: {str(e)}")
        return {"error": str(e)}

@calendar_bp.route('/event', methods=['POST'])  # заменяем @calendar_bp.event на @calendar_bp.route
def handle_event():
    data = request.get_json()  # получаем JSON данные из запроса
    date = data.get('date')

    if not date:
        emit('slots_update', {'error': 'Дата не выбрана!'})
        return

    logging.info(f"📅 Socket.IO: Получена дата от клиента: {date}")
    slots = get_slots_for_date(date)
    emit('slots_update', {'slots': slots})

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
        headers = values[0]
        records = [dict(zip(headers, row)) for row in values[1:]]
    class DummySheet:
        def get_all_records(self):
            return records
    return DummySheet()

def get_schedule_slots(day_of_week):
    """
    Загружает доступные слоты для конкретного дня недели из листа Schedule
    """
    sheet = get_google_sheet("Schedule")  # Загружаем лист
    slots = []
    for row in sheet.get_all_records():
        print(f"📅 {row}")  # Выводим все строки в консоль
        if row["day_of_week"].strip().lower() == day_of_week.strip().lower():
            slot_time = row["time"]
            max_participants = row["max_capacity"]
            slots.append({"time": slot_time, "max_participants": max_participants})
    print(f"🔍 Отфильтрованные слоты для {day_of_week}: {slots}")  # Проверяем, какие данные передаем
    return slots
