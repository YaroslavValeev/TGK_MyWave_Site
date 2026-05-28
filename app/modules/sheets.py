from flask import current_app
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import httplib2
from google_auth_httplib2 import AuthorizedHttp
from datetime import datetime
import uuid
from collections import defaultdict
import logging
from app.modules.sheets_access import get_google_sheet
from app.modules.logger import logger
from app.services.sheets_writer import save_client_workout_to_sheets
from app.database.models import db, Booking
from app.services.google_sheets_service import append_record

SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

def get_sheets_service():
    """
    Инициализирует клиент Google Sheets, используя сервисный аккаунт.
    Путь к credentials.json берётся из config.
    """
    creds_path = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    creds = Credentials.from_service_account_file(creds_path, scopes=SHEETS_SCOPES)
    authed_http = AuthorizedHttp(creds, http=httplib2.Http(timeout=10))
    return build('sheets', 'v4', http=authed_http, cache_discovery=False)

def get_sheet_records(service, spreadsheet_id, sheet_name):
    """
    Возвращает кортеж (records, headers):
    - records: list[dict], где ключ — заголовок, значение — ячейка
    - headers: list[str] — порядок колонок
    """
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:Z1000"
    ).execute()
    values = result.get("values", [])
    if not values:
        return [], []
    headers = values[0]
    records = [
        { headers[i]: row[i] if i < len(headers) else "" for i in range(len(headers)) }
        for row in values[1:]
    ]
    return records, headers

def append_to_sheet(service, spreadsheet_id, sheet_name, values: list[list]):
    """
    Записывает строки в конец листа:
    :param service: экземпляр sheets API
    :param spreadsheet_id: ID Google-таблицы
    :param sheet_name: имя листа (например, 'Clients')
    :param values: двумерный список значений для записи
    """
    body = {'values': values}
    return service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def get_or_create_client_id(
        name: str,
        phone: str,
        telegram_user_id: str = ''
) -> str:
    """
    Проверяет, существует ли клиент в листе Clients.
    Если нет — создаёт нового и возвращает client_id.
    """
    try:
        sheet = get_google_sheet('Clients')

        # 1️⃣ ищем по имени + телефону
        existing = sheet.find_rows(name=name, phone=phone)
        if existing:
            return existing[0][1].get("client_id")

        # 2️⃣ создаём новую запись согласно структуре
        new_id = f"client_{int(datetime.now().timestamp())}"
        created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_row = [
            new_id,                       # client_id
            telegram_user_id or '',       # telegram_user_id
            name,                         # name
            phone,                        # phone
            '',                           # email
            'beginner',                   # level
            created_at,                   # created_at
            'web',                        # source
            'new',                        # status
            '',                           # ref_code
            created_at                    # last_active
        ]

        spreadsheet_id = current_app.config.get('SPREADSHEET_ID')
        if spreadsheet_id:
            append_record(spreadsheet_id, 'Clients', new_row)
        return new_id
    except Exception as e:
        raise RuntimeError(f"Ошибка получения client_id: {e}")

def parse_time(time_str):
    """Преобразует строку времени 'HH:MM:SS' -> 'HH:MM', если есть секунды, иначе оставляет как есть."""
    try:
        return datetime.strptime(time_str, "%H:%M:%S").strftime("%H:%M")
    except ValueError:
        try:
            datetime.strptime(time_str, "%H:%M")
            return time_str
        except ValueError:
            raise ValueError(f"Invalid time format: {time_str}")

def append_row(sheet_name, values_list):
    """
    Добавляет одну строку (values_list) в конец листа sheet_name.
    Пример values_list: ["2025-01-01", "10:00", "Иван", "+79999999999"]

    Пример вызова:
      append_row("Client_Workouts", ["2025-01-01", "10:00", "Name", "+7..."])
    """
    service = get_sheets_service()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    body = {
        "values": [values_list]
    }

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def get_all_records(sheet_name):
    """
    Возвращает все записи листа sheet_name в виде списка словарей (list of dict).
    Первая строка листа рассматривается как заголовок.
    """
    service = get_sheets_service()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]

    # Запрашиваем все колонки вплоть до Z, при желании можно расширять до ZZ
    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:Z1000"
    ).execute()

    rows = result.get("values", [])
    if not rows or len(rows) < 2:
        return []  # Пустой лист или только заголовок

    headers = [h.strip().lower() for h in rows[0]]
    records = []
    for row in rows[1:]:
        # Формируем словарь {header: value} для каждой ячейки
        row_dict = {}
        for i, val in enumerate(row):
            key = headers[i] if i < len(headers) else f"extra_{i}"
            row_dict[key] = val.strip()
        records.append(row_dict)

    return records

def get_sheet_by_name(sheet_name):
    """
    Обёртка для get_all_records, если хочется короткий вызов.
    Возвращает двумерный список (list of list), а не list of dict.
    Если нужно dict, используйте get_all_records(sheet_name).
    """
    service = get_sheets_service()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]

    result = service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:J1000"
    ).execute()
    return result.get('values', [])

def normalize_time(time_str):
    try:
        return datetime.strptime(time_str.strip(), "%H:%M").strftime("%H:%M")
    except Exception:
        # попытка привести другой формат
        parts = time_str.strip().split(":")
        if len(parts) == 1:
            return f"{parts[0]}:00"
        elif len(parts) == 2:
            return f"{parts[0]}:{parts[1].zfill(2)}"
        return time_str

def get_workout_by_datetime(date: str, time: str):
    time = normalize_time(time)
    found = None
    for row in get_sheet_records("Workouts"):
        row_time = normalize_time(row.get("time", ""))
        if row.get("date") == date and row_time == time:
            cap = int(row.get("max_capacity", 0) or 0)
            found = {"workout_id": row.get("workout_id") or row.get("id"), "max_capacity": cap}
            break
    if not found:
        logging.warning(f"[⚠️] Тренировка {date} {time} не найдена в таблице Workouts")
        return None
    return found

def get_workout_participants(workout_id):
    """
    Считает количество записей в листе Client_Workouts,
    где workout_id совпадает со значением в третьей колонке (row[2]).
    """
    client_workouts = get_sheet_by_name("Client_Workouts")
    count = 0
    for row in client_workouts:
        if len(row) > 2 and row[2] == workout_id:
            count += 1
    return count

def add_client_workout(client_id: str,
                       workout_id: str,
                       date_str: str,
                       time_str: str) -> str:
    """
    Добавляет запись в лист Client_Workouts.
    Возвращает сгенерированный booking_id (UUID).
    """
    booking_id = str(uuid.uuid4())
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    new_booking = [
        booking_id,          # id
        client_id,           # client_id
        workout_id,          # workout_id
        date_str,            # date
        time_str,            # time
        "",                  # performance
        "",                  # feedback
        "",                  # payment_type
        "pending",           # status
        now,                 # created_at
        ""                   # client_rating
    ]

    append_row("Client_Workouts", new_booking)
    return booking_id

def add_or_update_client(telegram_user_id, name, phone, email=None):
    """
    Проверяем, есть ли клиент в листе "Clients".
    Если есть — обновляем last_active, если нет — добавляем.
    """
    print(f"🔄 Checking client: {telegram_user_id}")
    clients_data = get_sheet_by_name("Clients")

    # Ищем строку, где clients_data[i][0] == telegram_user_id
    client_row = None
    for i, row in enumerate(clients_data):
        if len(row) > 0 and str(row[0]) == str(telegram_user_id):
            client_row = i
            break

    service = get_sheets_service()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    today = datetime.now().strftime("%Y-%m-%d")

    if client_row is not None:
        # Обновляем last_active (в колонке F, это clients_data[i][5])
        range_name = f'Clients!F{client_row + 1}'
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body={'values': [[today]]}
        ).execute()
    else:
        # Добавляем новую запись
        new_client = [
            telegram_user_id,
            name,
            phone,
            email or "",
            "beginner", # Условный уровень
            today,      # last_active
            "telegram", # источник
            "new",      # статус
            "",         # доп. данные
            ""          # ещё поле
        ]
        service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range='Clients!A:J',
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body={'values': [new_client]}
        ).execute()

def update_workout_status(workout_id, status):
    """
    Обновляет статус тренировки в листе "Workouts" (допустим, в колонке H).
    """
    service = get_sheets_service()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    workouts = get_sheet_by_name("Workouts")

    for i, row in enumerate(workouts):
        if len(row) > 0 and row[0] == workout_id:
            # Статус в колонке H (index=7)
            range_name = f'Workouts!H{i+1}'
            service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption='RAW',
                body={'values': [[status]]}
            ).execute()
            break


def get_schedule_records():
    """
    Возвращает все записи с листа Schedule.
    Используется для отображения доступных слотов по дню недели.
    """
    records = get_sheet_records('Schedule')
    if not records:
        return []
    return records


def get_booked_slots(date):
    """
    Возвращает словарь вида {YYYY-MM-DD HH:MM: количество записей}, для конкретной даты.
    Использует связку Client_Workouts → Workouts:
    - В Workouts определяется, какие тренировки были на заданную дату.
    - В Client_Workouts ищутся записи на эти тренировки.
    """
    client_workouts = get_all_records("Client_Workouts")
    workouts = get_sheet_records("Workouts")          # list‑of‑dict
    target_workouts = {w["workout_id"]: w["time"]
                       for w in workouts
                       if w.get("date") == date}
    if not workouts or not client_workouts:
        return {}

    # Считаем, сколько человек записано на каждую тренировку по времени
    booked_slots = {}
    for record in client_workouts:
        workout_id = record.get("workout_id") or record.get("Workout ID") or record.get("workout ID")
        if workout_id in target_workouts:
            time = target_workouts[workout_id]
            key = f"{date} {time}"
            booked_slots[key] = booked_slots.get(key, 0) + 1

    return booked_slots


def add_workout(date_str, time_str, capacity):
    """
    Добавляет строку в таблицу Workouts. Используется при создании новой тренировки.
    Возвращает workout_id (строка).
    """
    workout_id = f"workout_{int(datetime.now().timestamp())}"
    new_row = [
        workout_id,         # workout_id
        date_str,           # date
        time_str,           # time
        "90",              # duration
        "Зал",             # location
        "групповая",       # workout_type
        str(capacity),      # max_capacity
        "Тренер",          # coach_name
        "активно",         # workout_status
        "0"                # current_capacity
    ]
    sheet = get_google_sheet("Workouts")
    sheet.append_row(new_row)
    return workout_id


def get_available_slots(check_date=None):
    """
    Возвращает список доступных слотов на определённую дату:
    [ {"time": ..., "available": ..., "booked": ..., "max_capacity": ...}, ... ]

    - Читает из листа Schedule (постоянное расписание).
    - Сравнивает со списком уже забронированных тренировок.
    - Фильтрует слоты, где свободных мест нет.
    """
    sheet = get_google_sheet("Schedule")
    current_date = check_date or datetime.now().strftime("%Y-%m-%d")
    booked_slots = get_booked_slots(current_date)
    day_of_week = datetime.strptime(current_date, "%Y-%m-%d").strftime("%A").strip().lower()

    slots = []
    logging.info(f"📅 Проверяем слоты на дату: {current_date} ({day_of_week})")

    for row in sheet.get_all_records():
        row_day = str(row.get("day_of_week", "")).strip().lower()
        if row_day != day_of_week:
            continue

        time = str(row.get("time", "")).strip()
        capacity_raw = str(row.get("max_capacity", "")).strip()

        if not time or not capacity_raw:
            continue

        try:
            max_capacity = int(capacity_raw)
        except ValueError:
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

    logging.info(f"✅ Найдено {len(slots)} слотов на {day_of_week}")
    return slots


def add_workout_to_sheet(date, time, client_id):
    """
    Добавляет тренировку в лист Workouts, используя client_id для получения name и phone из листа Clients.
    """
    service = get_sheets_service()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    clients = get_sheet_records("Clients")

    # Поиск данных клиента по client_id
    client_data = next((row for row in clients if row.get("client_id") == client_id), None)
    if not client_data:
        raise ValueError(f"❌ Клиент с ID '{client_id}' не найден в листе Clients")

    name = client_data.get("name", "").strip()
    phone = client_data.get("phone", "").strip()

    if not name or not phone:
        raise ValueError("❌ У клиента отсутствуют name или phone")

    range_name = "Workouts!A1"
    values = [[date, time, "90", "Зал", "групповая", "4", "Тренер", "активно", name, phone]]
    body = {"values": values}

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def is_valid_time_slot(time_str):
    # Пример простой валидации: слот должен быть в формате HH:MM и кратен 30 минутам
    try:
        h, m = map(int, time_str.split(":"))
        return 0 <= h < 24 and m in (0, 30)
    except Exception:
        return False

def book_slot(date_str, time_str, name, phone, service_type="gym"):
    """Path B: Calendar-first booking via unified pipeline."""
    if not is_valid_time_slot(time_str):
        logger.warning(f"Недопустимый слот времени: {time_str}")
        raise ValueError("Выбранное время недоступно для бронирования")

    from app.services.booking import (
        CalendarBookingError,
        DuplicateBookingError,
        execute_web_booking,
    )

    try:
        execute_web_booking(
            date=date_str,
            time=time_str,
            name=name,
            phone=phone,
            service_type=service_type or "gym",
        )
        return (
            True,
            "✅ Отлично! Ваша запись успешно подтверждена. Мы уже готовимся к вашей тренировке "
            "и свяжемся с вами для уточнения деталей. До встречи на воде! 🌊",
        )
    except DuplicateBookingError:
        return (False, "Вы уже записаны на это время.")
    except CalendarBookingError as e:
        logger.error("[booking] Calendar-first path failed: %s", e)
        return (False, "Не удалось создать запись в календаре. Попробуйте другой слот.")
    except Exception as e:
        logger.error("[booking] pipeline failed: %s", e, exc_info=True)
        return (False, "Не удалось создать запись. Попробуйте позже.")

def increment_capacity(workout_id: str):
    """
    +1 к колонке current_capacity у указанной тренировки.
    """
    sheet = get_google_sheet("Workouts")
    headers = sheet.values[0]
    row_idx  = None
    cap_col  = None

    for i, h in enumerate(headers):
        if h.strip().lower() == "current_capacity":
            cap_col = i
            break

    for r, row in enumerate(sheet.values[1:], start=2):
        if row and row[0] == workout_id:
            row_idx = r
            break

    if cap_col is None:
        logging.error(f"[❌] Колонка current_capacity не найдена в таблице Workouts")
        raise ValueError("Колонка current_capacity отсутствует")

    if row_idx:
        current = int(sheet.values[row_idx-1][cap_col] or 0)
        service = get_sheets_service()
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"Workouts!{chr(65+cap_col)}{row_idx}",
            valueInputOption="RAW",
            body={"values": [[current + 1]]}
        ).execute()

