import datetime
from app.modules.sheets_access import get_sheet_records, get_google_sheet
from google.oauth2 import service_account
from googleapiclient.discovery import build
import os
import json
import uuid

CALENDAR_ID = os.getenv("GOOGLE_CALENDAR_ID", "primary")

def get_google_calendar_service():
    credentials_path = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    if not credentials_path or not os.path.exists(credentials_path):
        raise Exception("Файл с учетными данными для Google Calendar не найден.")

    with open(credentials_path) as f:
        info = json.load(f)
    credentials = service_account.Credentials.from_service_account_info(info)
    service = build('calendar', 'v3', credentials=credentials)
    return service

def add_booking_to_calendar(date_str, time_str, name, phone):
    try:
        calendar_service = get_google_calendar_service()
        start_datetime = datetime.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
        end_datetime = start_datetime + datetime.timedelta(hours=1)

        event = {
            "summary": f"Тренировка: {name}",
            "description": f"Телефон: {phone}",
            "start": {"dateTime": start_datetime.isoformat(), "timeZone": "Europe/Moscow"},
            "end": {"dateTime": end_datetime.isoformat(), "timeZone": "Europe/Moscow"},
        }

        created_event = calendar_service.events().insert(
            calendarId=CALENDAR_ID,
            body=event,
            sendUpdates="all"
        ).execute()
        return True, created_event.get("htmlLink")
    except Exception as e:
        print(f"❌ Ошибка при добавлении в календарь: {e}")
        return False, str(e)

def create_workout_if_not_exists(date_str, time_str):
    sheet = get_google_sheet("Workouts")
    if not sheet.values or len(sheet.values) == 0:
        # Если лист пустой, создаём заголовки и первую строку
        headers = [
            "workout_id", "date", "time", "duration", "location", "workout_type",
            "max_capacity", "coach_name", "workout_status", "current_capacity"
        ]
        # Можно добавить первую строку-заголовок, если это поддерживается API
        append_to_sheet = __import__('app.modules.sheets_access', fromlist=['append_to_sheet']).append_to_sheet
        append_to_sheet('Workouts', headers)
        sheet = get_google_sheet("Workouts")
    headers = sheet.values[0]
    records = sheet.get_all_records()

    # Проверяем, существует ли уже тренировка на эту дату и время
    for idx, row in enumerate(records, start=2):  # начиная со строки 2
        if row.get("date") == date_str and row.get("time") == time_str:
            return row.get("workout_id")

    # Создаём новую тренировку
    new_id = f"workout_{date_str}_{time_str.replace(':', '')}"
    new_row = {
        "workout_id": new_id,
        "date": date_str,
        "time": time_str,
        "duration": 90,
        "location": "зал",
        "workout_type": "групповая",
        "max_capacity": 4,
        "coach_name": "Тренер",
        "workout_status": "активно",
        "current_capacity": 0
    }

    values = [new_row.get(header, "") for header in headers]
    append_to_sheet = __import__('app.modules.sheets_access', fromlist=['append_to_sheet']).append_to_sheet
    append_to_sheet('Workouts', values)
    return new_id
