import logging
import ssl
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import httplib2
from google_auth_httplib2 import AuthorizedHttp
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
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file or GOOGLE_SERVICE_ACCOUNT_FILE, 
        scopes=scopes
    )
    # Увеличиваем таймаут для SSL handshake и сетевых операций
    authed_http = AuthorizedHttp(credentials, http=httplib2.Http(timeout=30))
    service = build("sheets", "v4", http=authed_http, cache_discovery=False)
    return service

def get_sheet_data(credentials_file, sheet_id, worksheet_name):
    """
    Получение данных из таблицы Google Sheets через googleapiclient.
    Возвращает список словарей (строк).
    """
    try:
        service = get_sheets_service(credentials_file)
        # NB: В operational-табах (raw_feed) может быть много колонок (далеко за Z).
        # Расширяем диапазон, но оставляем ограничение по строкам для предсказуемости.
        range_name = f"{worksheet_name}!A1:ZZ1000"
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
        sheets_service = get_google_services()[1]  # Получаем только sheets сервис
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id or SPREADSHEET_ID,
            # NB: В operational-табах (raw_feed) может быть много колонок (далеко за Z).
            # Расширяем диапазон, но оставляем ограничение по строкам для предсказуемости.
            range=f"{(worksheet_name or GOOGLE_SHEET_NAME)}!A1:ZZ1000"
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
    except (ssl.SSLEOFError, ssl.SSLError, OSError) as ssl_err:
        error_msg = str(ssl_err)
        logger.error(f"SSL/сетевая ошибка при чтении из Google Sheets: {error_msg}")
        # Преобразуем SSL ошибки в TimeoutError для единообразной обработки
        raise TimeoutError(f"Сетевая ошибка при подключении к Google Sheets: {error_msg}") from ssl_err
    except HttpError as he:
        error_msg = str(he)
        logger.error(f"Ошибка API Google Sheets: {error_msg}")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка чтения из Google Sheets: {error_msg}")
        # Проверяем, не является ли это SSL таймаутом в сообщении об ошибке
        if "timeout" in error_msg.lower() or "handshake" in error_msg.lower() or "ssl" in error_msg.lower() or "eof" in error_msg.lower():
            raise TimeoutError(f"Таймаут при подключении к Google Sheets: {error_msg}") from e
        raise

def append_record(spreadsheet_id=None, worksheet_name=None, values=None):
    """Добавляет запись в Google Sheets."""
    if values is None:
        raise ValueError("Значения для записи не указаны")
    try:
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
    except (ssl.SSLEOFError, ssl.SSLError, OSError) as ssl_err:
        error_msg = str(ssl_err)
        logger.error(f"SSL/сетевая ошибка при добавлении записи в Google Sheets: {error_msg}")
        raise TimeoutError(f"Сетевая ошибка при подключении к Google Sheets: {error_msg}") from ssl_err
    except HttpError as he:
        error_msg = str(he)
        logger.error(f"Ошибка API Google Sheets при добавлении записи: {error_msg}")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка добавления записи в Google Sheets: {error_msg}")
        if "timeout" in error_msg.lower() or "handshake" in error_msg.lower() or "ssl" in error_msg.lower() or "eof" in error_msg.lower():
            raise TimeoutError(f"Таймаут при подключении к Google Sheets: {error_msg}") from e
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
    except (ssl.SSLEOFError, ssl.SSLError, OSError) as ssl_err:
        error_msg = str(ssl_err)
        logger.error(f"SSL/сетевая ошибка при обновлении записи в Google Sheets: {error_msg}")
        raise TimeoutError(f"Сетевая ошибка при подключении к Google Sheets: {error_msg}") from ssl_err
    except HttpError as he:
        error_msg = str(he)
        logger.error(f"Ошибка API Google Sheets при обновлении записи: {error_msg}")
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка обновления записи в Google Sheets: {error_msg}")
        if "timeout" in error_msg.lower() or "handshake" in error_msg.lower() or "ssl" in error_msg.lower() or "eof" in error_msg.lower():
            raise TimeoutError(f"Таймаут при подключении к Google Sheets: {error_msg}") from e
        raise
