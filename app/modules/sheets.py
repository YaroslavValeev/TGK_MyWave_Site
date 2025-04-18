from flask import current_app
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from datetime import datetime
import uuid
from collections import defaultdict
from app.modules.sheets_access import get_sheet_records, SheetWrapper, get_google_sheet, append_to_sheet, SheetWrapper

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

        append_to_sheet('Clients', new_row)
        return new_id
    except Exception as e:
        raise RuntimeError(f"Ошибка получения client_id: {e}")

def get_sheets_service():
    """
    Инициализируем клиент Google Sheets, используя сервисный аккаунт.
    Путь к credentials.json берём либо из config, либо используем захардкоженный вариант.
    """
    creds_path = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE", "credentials.json")
    creds = Credentials.from_service_account_file(creds_path)
    return build('sheets', 'v4', credentials=creds)

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

def get_workout_by_datetime(date: str, time: str):
    """
    Ищем строку, где date == YYYY‑MM‑DD и time == HH:MM.
    """
    for row in get_sheet_records("Workouts"):
        if row.get("date") == date and row.get("time") == time:
            cap = int(row.get("max_capacity", 0) or 0)
            return {"workout_id": row.get("workout_id") or row.get("id"),
                    "max_capacity": cap}
    return None

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
    Возвращает номер строки после добавления (может использоваться как workout_id).
    """
    sheet = get_google_sheet("Workouts")
    new_row = [f"{date_str} {time_str}", 90, "MyWave", "индивидуальная", capacity, "Ярослав"]
    sheet.append_row(new_row)
    return sheet.row_count


def get_available_slots(check_date=None):
    """
    Возвращает список доступных слотов на определённую дату:
    [ {"time": ..., "available": ..., "booked": ..., "max_capacity": ...}, ... ]

    - Читает из листа Schedule (постоянное расписание).
    - Сравнивает со списком уже забронированных тренировок.
    - Фильтрует слоты, где свободных мест нет.
    """
    import logging
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

def book_slot(date_str, time_str, name, phone):
    """
    Осуществляет запись:
      1) Проверяет доступность слота
      2) Создаёт тренировку в Workouts (если нет)
      3) Добавляет клиента в Client_Workouts
      4) Создаёт событие в Google Calendar
    Возвращает (True, calendar_link) или (False, "Error text")
    """
    try:
        # Получаем client_id
        client_id = get_or_create_client_id(name, phone)

        # 1. Проверяем доступность слота
        is_ok, msg = is_slot_available(date_str, time_str)
        if not is_ok:
            return (False, msg)

        # 2. Пытаемся найти тренировку в Workouts
        workout = get_workout_by_datetime(date_str, time_str)

        # Если не нашли — создаём
        if not workout:
            workout_id = create_workout_if_not_exists(date_str, time_str)
            if not workout_id:
                return (False, "Не удалось создать тренировку")
            workout = get_workout_by_datetime(date_str, time_str)
            if not workout:
                return (False, "Тренировка была создана, но не найдена при повторном поиске. Проверьте структуру данных.")
        else:
            workout_id = workout["workout_id"]

        # 3. Проверяем количество участников
        participants = get_workout_participants(workout_id)
        if participants >= workout["max_capacity"]:
            return (False, "Слот переполнен")

        # 4. Добавляем клиента
        add_client_workout(client_id, workout_id, date_str, time_str)

        # 4‑bis. ⬆️ Инкрементируем current_capacity
        increment_capacity(workout_id)

        # 5. Создаём событие в календаре
        success, link = add_booking_to_calendar(date_str, time_str, name, phone)
        if success:
            return (True, link)
        else:
            return (False, "Ошибка добавления в Google Calendar")

    except Exception as e:
        return (False, str(e))

def increment_capacity(workout_id: str):
    """
    +1 к колонке current_capacity у указанной тренировки.
    """
    sheet = get_google_sheet("Workouts")
    headers = sheet.values[0]
    row_idx  = None
    cap_col  = None

    # находим строку и индекс колонки
    for i, h in enumerate(headers):
        if h.strip().lower() == "current_capacity":
            cap_col = i
            break

    for r, row in enumerate(sheet.values[1:], start=2):   # A2…
        if row and row[0] == workout_id:                   # A‑столбец — workout_id
            row_idx = r
            break

    if row_idx and cap_col is not None:
        current = int(sheet.values[row_idx-1][cap_col] or 0)
        service = get_sheets_service()
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=f"Workouts!{chr(65+cap_col)}{row_idx}",
            valueInputOption="RAW",
            body={"values": [[current + 1]]}
        ).execute()

