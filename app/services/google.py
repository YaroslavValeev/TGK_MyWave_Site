import os
import json
import logging
import datetime
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google_auth_oauthlib.flow import Flow
import httpx
from google.auth.transport.requests import Request
from google.auth.transport.requests import AuthorizedSession
from flask import current_app
from googleapiclient.http import MediaIoBaseUpload
import io

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

_drive = _sheets = _calendar = None

def get_google_services():
    """
    Лениво инициализирует и кеширует сервисы Google Drive, Sheets и Calendar.
    Берёт путь к service account из current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"].
    """
    global _drive, _sheets, _calendar
    
    # Проверяем кеш сервисов
    if _drive and _sheets and _calendar:
        return _drive, _sheets, _calendar

    creds_path = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not creds_path:
        msg = "GOOGLE_SERVICE_ACCOUNT_FILE не задан в конфигурации"
        logging.critical(msg)
        raise ValueError(msg)

    if not os.path.isfile(creds_path):
        msg = f"Файл сервисного аккаунта не найден: {creds_path}"
        logging.critical(msg)
        raise FileNotFoundError(msg)

    # Максимальное количество попыток подключения
    max_retries = 3
    retry_delay = 1  # начальная задержка в секундах

    for attempt in range(max_retries):
        try:
            # Читаем файл сервисного аккаунта
            with open(creds_path, 'r', encoding='utf-8') as f:
                service_account_info = json.load(f)
            
            # Форматируем private_key
            if 'private_key' in service_account_info:
                service_account_info['private_key'] = service_account_info['private_key'].replace('\\n', '\n')
            
            # Создаем credentials
            creds = service_account.Credentials.from_service_account_info(
                service_account_info,
                scopes=SCOPES
            )
            
            # Пробуем обновить токен с таймаутом
            with httpx.Client(timeout=10.0) as client:
                try:
                    request = Request(session=client)
                    creds.refresh(request)
                except Exception as e:
                    current_app.logger.warning(f"Попытка {attempt + 1}: Ошибка обновления токена: {e}")
                    if attempt == max_retries - 1:  # Если это последняя попытка
                        raise
            
            # Создаем сервисы с увеличенным таймаутом
            _drive = build("drive", "v3", credentials=creds, cache_discovery=False)
            _sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
            _calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
            
            # Проверяем подключение через тестовый запрос
            try:
                spreadsheet_id = current_app.config.get('SPREADSHEET_ID')
                if spreadsheet_id:
                    _sheets.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
            except Exception as e:
                if 'invalid_grant' in str(e):
                    msg = "Неверная подпись JWT. Проверьте private_key в файле сервисного аккаунта"
                    logging.critical(msg)
                    raise ValueError(msg)
                elif any(err in str(e) for err in ['WSAENETUNREACH', 'getaddrinfo failed']):
                    if attempt < max_retries - 1:
                        current_app.logger.warning(f"Попытка {attempt + 1}: Проблема с сетью, повторная попытка через {retry_delay} сек")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Увеличиваем задержку экспоненциально
                        continue
                raise

            logging.info(f"✅ Google services initialized (попытка {attempt + 1})")
            return _drive, _sheets, _calendar

        except Exception as e:
            if attempt < max_retries - 1:
                current_app.logger.warning(f"Попытка {attempt + 1} не удалась: {e}")
                import time
                time.sleep(retry_delay)
                retry_delay *= 2
                continue
            logging.critical(f"Failed to initialize Google services after {max_retries} attempts: {e}")
            raise

def read_sheet(spreadsheet_id: str, sheet_name: str) -> tuple[list[dict], list[str]]:
    svc = get_google_services()[1]
    result = svc.spreadsheets().values().get(
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

def append_to_sheet(spreadsheet_id: str, sheet_name: str, values: list[list]):
    svc = get_google_services()[1]
    body = {"values": values}
    return svc.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

def GoogleService(service_account_file=None):
    try:
        if not service_account_file:
            service_account_file = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")

        if not service_account_file or not os.path.exists(service_account_file):
            raise FileNotFoundError(f"Файл сервисного аккаунта не найден: {service_account_file}")

        with open(service_account_file, 'r', encoding='utf-8') as file:
            service_account_info = json.load(file)

        creds = Credentials.from_service_account_info(
            service_account_info,
            scopes=SCOPES
        )

        drive_service = build("drive", "v3", credentials=creds)
        sheet_service = build("sheets", "v4", credentials=creds)
        calendar_service = build("calendar", "v3", credentials=creds)
        
        logging.info("✅ Google API успешно инициализирован!")

        return drive_service, sheet_service, calendar_service

    except json.JSONDecodeError as e:
        logging.critical(f"❌ Ошибка чтения JSON файла сервисного аккаунта: {str(e)}")
        raise
    except Exception as e:
        logging.critical(f"❌ Ошибка инициализации сервисов Google: {str(e)}")
        raise

def add_event_to_calendar(service, date, time, client_name, client_phone):
    try:
        calendar_id = current_app.config.get('GOOGLE_CALENDAR_ID')
        if not calendar_id:
            logging.warning('⚠️ GOOGLE_CALENDAR_ID не настроен, событие не будет добавлено в календарь')
            return False
        
        start_time = datetime.strptime(f'{date} {time}', '%Y-%m-%d %H:%M')
        end_time = start_time + timedelta(hours=1, minutes=30)
        timezone = current_app.config.get('TIMEZONE', 'Europe/Moscow')

        event_body = {
            'summary': f'Тренировка: {client_name}',
            'description': f'Телефон: {client_phone}',
            'start': {'dateTime': start_time.isoformat(), 'timeZone': timezone},
            'end': {'dateTime': end_time.isoformat(), 'timeZone': timezone},
        }

        service[2].events().insert(
            calendarId=calendar_id,
            body=event_body
        ).execute()

        logging.info('✅ Запись успешно добавлена в календарь')
        return True

    except Exception as e:
        logging.error(f'❌ Ошибка добавления события в календарь: {e}')
        return False

def upload_to_drive(service, file_obj, user_id, folder_id):
    try:
        file_obj.seek(0)
        file_metadata = {
            "name": f"{user_id}_{file_obj.filename}",
            "parents": [folder_id]
        }
        media = MediaIoBaseUpload(file_obj.stream, mimetype=file_obj.content_type, resumable=True)
        uploaded_file = service[0].files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()
        logging.info("Файл успешно загружен: %s", uploaded_file.get("id"))
        file_id = uploaded_file.get("id")
        webViewLink = uploaded_file.get("webViewLink", create_drive_link(file_id))
        return file_id, webViewLink
    except Exception as e:
        logging.error("Ошибка загрузки файла на Google Drive: %s", str(e))
        raise

def list_user_files(service, folder_id, user_id):
    try:
        query = f"'{folder_id}' in parents and trashed=false and name contains '{user_id}_'"
        results = service[0].files().list(
            q=query,
            fields="files(id, name, webViewLink)"
        ).execute()
        files = results.get("files", [])
        logging.info("Найдено файлов для пользователя %s: %d", user_id, len(files))
        return files
    except Exception as e:
        logging.error("Ошибка получения списка файлов: %s", str(e))
        raise

def create_drive_link(file_id):
    """
    Creates a shareable Google Drive link for the given file ID
    
    Args:
        file_id (str): Google Drive file ID
        
    Returns:
        str: Shareable Google Drive link
    """
    try:
        link = f"https://drive.google.com/file/d/{file_id}/view"
        logging.info("Создана ссылка для файла: %s", link)
        return link
    except Exception as e:
        logging.error("Ошибка создания ссылки для файла: %s", str(e))
        raise

def get_available_slots(service, start_date, end_date):
    try:
        # Get events from calendar
        events_result = service[2].events().list(
            calendarId=current_app.config['GOOGLE_CALENDAR_ID'],
            timeMin=start_date.isoformat() + 'Z',
            timeMax=end_date.isoformat() + 'Z',
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        events = events_result.get('items', [])

        # Process bookings
        booked_slots = {}
        for event in events:
            start = datetime.fromisoformat(event['start']['dateTime'])
            slot_key = start.strftime('%Y-%m-%d %H:%M')
            # Extract participant count from event description if available
            description = event.get('description', '')
            participants = 1  # Default to 1 if not specified
            if 'Участники:' in description:
                try:
                    participants = int(description.split('Участники:')[1].strip())
                except ValueError:
                    pass
            
            booked_slots[slot_key] = booked_slots.get(slot_key, 0) + participants

        # Calculate available slots
        max_capacity = current_app.config.get('MAX_SLOT_CAPACITY', 4)
        available_slots = {}
        for slot, count in booked_slots.items():
            available_slots[slot] = max_capacity - count

        return available_slots

    except Exception as e:
        logging.error(f'❌ Ошибка получения доступных слотов: {e}')
        return {}

def upload_file_to_drive(file_content: bytes, filename: str):
    """Загрузка файла в Google Drive"""
    creds_path = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    folder_id = current_app.config.get("DRIVE_FOLDER_ID")

    if not creds_path or not folder_id:
        raise ValueError("Отсутствуют переменные окружения: GOOGLE_SERVICE_ACCOUNT_FILE или DRIVE_FOLDER_ID")

    credentials = service_account.Credentials.from_service_account_file(creds_path)
    drive_service = build('drive', 'v3', credentials=credentials)

    media = MediaIoBaseUpload(io.BytesIO(file_content), mimetype='application/octet-stream')

    file_metadata = {
        'name': filename,
        'parents': [folder_id]
    }

    uploaded_file = drive_service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id, webViewLink, webContentLink'
    ).execute()

    return {
        "file_id": uploaded_file.get("id"),
        "view_link": uploaded_file.get("webViewLink"),
        "download_link": uploaded_file.get("webContentLink")
    }
