from flask import current_app
import datetime
import logging
from app.modules.sheets_access import get_google_sheet
from app.modules.sheets import (
    get_booked_slots,
    get_sheet_records,
    get_sheets_service,
    get_schedule_records,
    get_workout_by_datetime,
    get_workout_participants,
    add_client_workout,
    get_or_create_client_id,
    SheetWrapper
)
from app.modules.calendar_integration import add_booking_to_calendar, create_workout_if_not_exists

def get_workout_by_datetime(date_str: str, time_str: str):
    """
    Находит тренировку в листе Workouts по дате и времени.
    Поддерживает оба варианта структуры:
      • единая колонка  date_time      ("YYYY‑MM‑DD HH:MM")
      • отдельные       date + time    ("YYYY‑MM‑DD", "HH:MM")
    Возвращает словарь {workout_id, max_capacity} или None.
    """
    try:
        records = get_sheet_records("Workouts")
        if not records:
            return None

        target = f"{date_str} {time_str}"

        for row in records:
            # 1️⃣  Пробуем «старый» формат ─ date_time
            date_time = str(row.get("date_time", "")).strip()

            # 2️⃣  Если его нет ─ собираем из двух колонок
            if not date_time:
                date_val = str(row.get("date", "")).strip()
                time_val = str(row.get("time", "")).strip()
                if date_val and time_val:
                    date_time = f"{date_val} {time_val}"

            # 3️⃣  Сравниваем с целевым значением
            if date_time == target:
                workout_id = (
                    row.get("workout_id")
                    or row.get("id")
                    or row.get("ID")
                )
                capacity = (
                    row.get("max_capacity")
                    or row.get("capacity")
                    or 0
                )
                return {
                    "workout_id": workout_id,
                    "max_capacity": int(capacity) if str(capacity).isdigit() else 0,
                }

    except Exception as e:
        logging.exception(f"❌ Ошибка при поиске тренировки: {e}")

    return None


def is_slot_available(date_str, time_str):
    """
    Проверяет, есть ли свободные места на указанную дату/время.
    Возвращает (bool, message), где bool = доступность, message = причина или комментарий.
    """
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        datetime.datetime.strptime(time_str, "%H:%M")

        booked = get_booked_slots(date_str)
        key = f"{date_str} {time_str}"
        current_bookings = booked.get(key, 0)

        capacity = get_slot_capacity(date_str, time_str)
        if capacity is None:
            return False, "Тренировка не найдена на указанное время"

        if current_bookings >= capacity:
            return False, "Нет свободных мест"

        return True, ""
    except ValueError as e:
        return False, f"Неверный формат даты/времени: {str(e)}"


def get_slot_capacity(date_str, time_str):
    """
    Возвращает вместимость слота (int) или None, если слот не найден.
    """
    try:
        date_obj = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        day_of_week = date_obj.strftime("%A").strip().lower()

        schedule = get_schedule_records()

        for row in schedule:
            row_day = str(row.get("day_of_week", "")).strip().lower()
            row_time = str(row.get("time", "")).strip()

            if row_day == day_of_week and row_time == time_str:
                capacity_raw = str(row.get("max_capacity", "")).strip()
                if capacity_raw.isdigit():
                    return int(capacity_raw)
                else:
                    return None

        return None
    except Exception as e:
        print(f"❌ Ошибка получения capacity: {e}")
        return None


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


def book_slot(date_str, time_str, name, phone):
    logging.info(f"⚙️ Старт бронирования: {name} {phone} → {date_str} {time_str}")
    """
    Осуществляет запись:
      1) Проверяет доступность слота
      2) Создаёт тренировку в Workouts (если нет)
      3) Добавляет клиента в Client_Workouts
      4) Создаёт событие в Google Calendar
    Возвращает (True, calendar_link) или (False, "Error text")
    """
    try:
        # 1. Проверяем доступность слота
        is_ok, msg = is_slot_available(date_str, time_str)
        if not is_ok:
            return (False, msg)

        # 2. Получаем client_id
        client_id = get_or_create_client_id(name, phone)

        # 3. Пытаемся найти тренировку в Workouts
        workout = get_workout_by_datetime(date_str, time_str)
        if not workout:
            workout_id = create_workout_if_not_exists(date_str, time_str)
            if not workout_id:
                return (False, "Не удалось создать тренировку")
            workout = get_workout_by_datetime(date_str, time_str)
        else:
            workout_id = workout["workout_id"]

        # 4. Проверяем количество участников
        participants = get_workout_participants(workout_id)
        if participants >= workout["max_capacity"]:
            return (False, "Слот переполнен")

        # 5. Добавляем клиента
        add_client_workout(client_id, workout_id, date_str, time_str)

        # 5‑bis. ⬆️ Инкрементируем current_capacity
        increment_capacity(workout_id)

        # 6. Создаём событие в календаре
        success, link = add_booking_to_calendar(date_str, time_str, name, phone)
        if success:
            return (True, link)
        else:
            return (False, "Ошибка добавления в Google Calendar")

    except Exception as e:
        return (False, str(e))

