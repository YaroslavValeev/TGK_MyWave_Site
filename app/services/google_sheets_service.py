import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import os
from app.services.google import get_google_services
from app.config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    SPREADSHEET_ID,
    GOOGLE_SHEET_NAME
)

# Настрой логирование
logger = logging.getLogger(__name__)

def get_sheets_service(credentials_file=None):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    # Prefer central factory when no explicit credentials_file is passed.
    if not credentials_file:
        try:
            # get_google_services already handles GOOGLE_MOCK/DEBUG and will return mock services when appropriate
            return get_google_services()[1]
        except Exception:
            # Fall through to file-based creation below if central factory fails for any reason
            credentials_file = GOOGLE_SERVICE_ACCOUNT_FILE

    if not credentials_file:
        raise ValueError("No credentials file provided for Google Sheets service")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=scopes
    )
    service = build("sheets", "v4", credentials=credentials)
    return service

def get_sheet_data(credentials_file, sheet_id, worksheet_name):
    """
    Получение данных из таблицы Google Sheets через googleapiclient.
    Возвращает список словарей (строк).
    """
    try:
        service = get_sheets_service(credentials_file)
        range_name = f"{worksheet_name}!A1:Z1000"
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id,
            range=range_name
        ).execute()
        values = result.get("values", [])
        if not values:
            logger.warning(f"Таблица {worksheet_name} пуста")
            return []
        headers = values[0]
        records = []
        for row in values[1:]:
            record = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            records.append(record)
        return records
    except Exception as e:
        logger.error(f"Ошибка получения данных из таблицы: {str(e)}")
        return []

def append_to_sheet(credentials_file, sheet_id, worksheet_name, row_data):
    """
    Запись данных в таблицу Google Sheets через googleapiclient.
    """
    try:
        if not isinstance(row_data, list):
            raise ValueError("Данные должны быть в виде списка")
        service = get_sheets_service(credentials_file)
        range_name = f"{worksheet_name}!A1:Z1000"
        body = {"values": [row_data]}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        logger.info(f"Данные успешно добавлены в таблицу {worksheet_name}")
    except Exception as e:
        logger.error(f"Ошибка записи данных в таблицу: {str(e)}")
        raise

def get_history_by_client_id(credentials_file, sheet_id, worksheet_name, client_id):
    """
    Получение всей истории сообщений по client_id через googleapiclient.
    """
    try:
        records = get_sheet_data(credentials_file, sheet_id, worksheet_name)
        return [
            {"role": "user", "content": row["message"]}
            for row in records if row.get("client_id") == client_id
        ]
    except Exception as e:
        logger.error(f"Ошибка получения истории сообщений: {str(e)}")
        return []

def save_message(credentials_file, sheet_id, worksheet_name, client_id, message):
    """
    Сохраняет новое сообщение в таблицу через googleapiclient.
    """
    try:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        row_data = [client_id, now, message]
        append_to_sheet(credentials_file, sheet_id, worksheet_name, row_data)
    except Exception as e:
        logger.error(f"Ошибка сохранения сообщения: {str(e)}")
        raise

def read_records(spreadsheet_id=None, worksheet_name=None):
    """Читает записи из Google Sheets."""
    try:
        # In testing/mock mode, avoid real Google API calls
        from flask import current_app as _current_app
        if getattr(_current_app, 'config', {}).get('GOOGLE_MOCK'):
            return []
        sheets_service = get_google_services()[1]  # Получаем только sheets сервис
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id or SPREADSHEET_ID,
            range=f"{(worksheet_name or GOOGLE_SHEET_NAME)}!A1:Z1000"
        ).execute()
        values = result.get('values', [])
        if not values:
            return []
        headers = values[0]
        records = []
        for row in values[1:]:
            record = {}
            for i, value in enumerate(row):
                if i < len(headers):
                    record[headers[i]] = value
            records.append(record)
        return records
    except Exception as e:
        logger.error(f"Ошибка чтения из Google Sheets: {e}")
        raise

def append_record(spreadsheet_id=None, worksheet_name=None, values=None):
    """Добавляет запись в Google Sheets."""
    if values is None:
        raise ValueError("Значения для записи не указаны")
    try:
        from flask import current_app as _current_app
        if getattr(_current_app, 'config', {}).get('GOOGLE_MOCK'):
            # Testing mode: don't call external API
            return {'mock': True}
        sheets_service = get_google_services()[1]
        body = {
            'values': [values] if not isinstance(values[0], list) else values
        }
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id or SPREADSHEET_ID,
            range=f"{(worksheet_name or GOOGLE_SHEET_NAME)}!A1",
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        return result
    except Exception as e:
        logger.error(f"Ошибка добавления записи в Google Sheets: {e}")
        raise

def update_record(spreadsheet_id=None, worksheet_name=None, range_=None, values=None):
    """Обновляет запись в Google Sheets."""
    if values is None or range_ is None:
        raise ValueError("Не указаны значения или диапазон для обновления")
    try:
        sheets_service = get_google_services()[1]
        body = {
            'values': [values] if not isinstance(values[0], list) else values
        }
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id or SPREADSHEET_ID,
            range=f"{(worksheet_name or GOOGLE_SHEET_NAME)}!{range_}",
            valueInputOption='RAW',
            body=body
        ).execute()
        return result
    except Exception as e:
        logger.error(f"Ошибка обновления записи в Google Sheets: {e}")
        raise
