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
    # SheetWrapper,  # Уже закомментировано
    increment_capacity,
    # get_slot_capacity,  # Удалено
    book_slot
)
from app.modules.calendar_integration import add_booking_to_calendar, create_workout_if_not_exists
import os
import requests
from app.modules.logger import get_logger

logger = get_logger(__name__)

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

        workout = get_workout_by_datetime(date_str, time_str)
        if not workout:
            return False, "Тренировка не найдена на указанное время"
        capacity = workout.get("max_capacity", 0)

        if current_bookings >= capacity:
            return False, "Нет свободных мест"

        return True, ""
    except ValueError as e:
        return False, f"Неверный формат даты/времени: {str(e)}"


def send_telegram_message(text):
    token = os.getenv("NOTIFICATION_BOT_TOKEN")
    chat_id = os.getenv("ADMIN_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data={"chat_id": chat_id, "text": text}
        )
    except Exception as e:
        print(f"Ошибка отправки Telegram: {e}")


def handle_booking(data):
    return book_slot(data["date"], data["time"], data["name"], data["phone"])

