import datetime
import logging
import os
import json
import uuid
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.database.models import db, CalendarEvent
from app.modules.sheets import append_row
from app.modules.sheets_access import get_sheet_records, get_google_sheet, append_dict_to_sheet
from app.services.google_sheets_service import update_record

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

def create_workout_if_not_exists(date_str, time_str, showcase_id=None, slot_type=None, service_type=None):
    sheet = get_google_sheet("Workouts")
    if not sheet.values or len(sheet.values) == 0:
        # Если лист пустой, создаём заголовки и первую строку
        headers = [
            "workout_id", "date", "time", "duration", "location", "workout_type",
            "max_capacity", "coach_name", "workout_status", "current_capacity", "service_type"
        ]
        # Можно добавить первую строку-заголовок, если это поддерживается API
        append_to_sheet = __import__('app.modules.sheets_access', fromlist=['append_to_sheet']).append_to_sheet
        append_to_sheet('Workouts', headers)
        sheet = get_google_sheet("Workouts")
    headers = sheet.values[0]
    records = sheet.get_all_records()

    # Если в листе ещё нет колонки service_type (K), добавляем её в заголовок
    if "service_type" not in headers:
        try:
            update_record(worksheet_name="Workouts", range_="A1", values=headers + ["service_type"])
            sheet = get_google_sheet("Workouts")
            headers = sheet.values[0]
            records = sheet.get_all_records()
        except Exception as e:
            logging.error(f"Не удалось добавить колонку service_type в Workouts: {e}")

    normalized_service_type = (service_type or slot_type or "boat").strip().lower()

    # Проверяем, существует ли уже тренировка на эту дату и время
    for idx, row in enumerate(records, start=2):  # начиная со строки 2
        if row.get("date") == date_str and row.get("time") == time_str:
            existing_service_type = (row.get("service_type") or "").strip().lower()

            # Если тренировка найдена, но поле service_type пустое — заполняем его значением по умолчанию
            if not existing_service_type:
                try:
                    col_idx = headers.index("service_type")
                    col_letter = chr(ord('A') + col_idx)
                    update_record(
                        worksheet_name="Workouts",
                        range_=f"{col_letter}{idx}",
                        values=[normalized_service_type]
                    )
                except Exception as e:
                    logging.error(
                        "Не удалось обновить service_type для существующей тренировки %s %s: %s",
                        date_str,
                        time_str,
                        e,
                    )

            return row.get("workout_id")

    # Создаём новую тренировку
    new_id = f"workout_{date_str}_{time_str.replace(':', '')}"
    new_row = {
        "workout_id": new_id,
        "date": date_str,
        "time": time_str,
        "duration": 90,
        "location": "зал" if not showcase_id else f"зал | {showcase_id}",
        "workout_type": slot_type or "групповая",
        "max_capacity": 4,
        "coach_name": "Тренер",
        "workout_status": "активно",
        "current_capacity": 0,
        "service_type": normalized_service_type
    }
    # Используем универсальную функцию для записи
    append_dict_to_sheet('Workouts', new_row)
    return new_id

# Новая функция с валидацией, логированием и синхронной записью

def create_calendar_event(event_data):
    if not event_data.get('start') or not event_data.get('summary'):
        raise ValueError("Missing required calendar fields")
    service = get_google_calendar_service()
    try:
        created = service.events().insert(calendarId=CALENDAR_ID, body=event_data).execute()
    except HttpError as e:
        logging.error(f"Calendar insert failed: {e}")
        raise
    # Сохраняем в БД
    db_event = CalendarEvent.from_api(created)
    db.session.add(db_event)
    db.session.commit()
    # Сохраняем в Google Sheets
    append_row("CalendarEvents", [created['id'], event_data['start'], event_data['summary']])
    return created
