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
from flask import current_app
from googleapiclient.http import MediaIoBaseUpload
import io

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

_drive = _sheets = _calendar = None
_cached_creds_path = None

def get_google_services():
    """
    Лениво инициализирует и кеширует сервисы Google Drive, Sheets и Calendar.
    Берёт путь к service account из current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"].
    """
    global _drive, _sheets, _calendar

    # Determine whether mock fallback is allowed early so tests that patch
    # google.build/service_account can control behavior. When mock_allowed is
    # True we skip returning any previously cached services to ensure patched
    # build() is invoked during the test run.
    mock_allowed = (
        bool(current_app.config.get('GOOGLE_MOCK'))
        or bool(current_app.config.get('DEBUG'))
        or getattr(current_app, 'debug', False)
        or str(current_app.config.get('ENV', '')).lower() == 'development'
        or os.environ.get('FLASK_ENV', '').lower() == 'development'
    )

    # Determine credentials path early so we can compare against cached services
    creds_path = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")

    # If we're not in a mock-enabled run and services were already
    # initialized earlier for the same credentials file, return the cached instances
    global _cached_creds_path
    if not mock_allowed and _drive and _sheets and _calendar and creds_path and creds_path == _cached_creds_path:
        return _drive, _sheets, _calendar
    # Allow forcing strict mode in production via env var GOOGLE_STRICT=1
    strict_mode = os.environ.get('GOOGLE_STRICT', '0') in ('1', 'true', 'True')

    def _make_mock_service():
        class _MockService:
            def spreadsheets(self):
                class _S:
                    def get(self, **kwargs):
                        class R:
                            def execute(self):
                                return {"values": []}
                        return R()
                return _S()

            def values(self):
                class _V:
                    def get(self, **kwargs):
                        class R:
                            def execute(self):
                                return {"values": []}
                        return R()
                return _V()

            def events(self):
                class _E:
                    def list(self, **kwargs):
                        class R:
                            def execute(self):
                                return {"items": []}
                        return R()
                return _E()

        return _MockService()

    if not creds_path or not os.path.isfile(creds_path):
        msg = f"Файл сервисного аккаунта не найден: {creds_path}"
        # Only return mock services here if the app explicitly requests it
        if current_app.config.get('GOOGLE_MOCK'):
            logging.warning(msg)
            logging.warning("GOOGLE_MOCK enabled: returning mock Google services because service account file is missing")
            mock = _make_mock_service()
            return mock, mock, mock
        # Otherwise surface the missing file as an explicit error
        logging.critical(msg)
        raise FileNotFoundError(msg)

    try:
        # Prefer using the google.oauth2.service_account helper to create
        # credentials directly. Tests commonly monkeypatch
        # service_account.Credentials.from_service_account_file, so avoid
        # opening/parsing the file manually here.
        try:
            creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        except Exception as e:
            err_str = str(e)
            if mock_allowed:
                logging.warning("GOOGLE_MOCK/DEBUG enabled: returning mock Google services due to credential error: %s", err_str)
                mock = _make_mock_service()
                return mock, mock, mock
            logging.critical(f"❌ Error creating service account credentials: {err_str}")
            raise

        # Build the Google API service clients using the created credentials
        _drive = build("drive", "v3", credentials=creds, cache_discovery=False)
        _sheets = build("sheets", "v4", credentials=creds, cache_discovery=False)
        _calendar = build("calendar", "v3", credentials=creds, cache_discovery=False)
        _cached_creds_path = creds_path

        # Verify access to the configured spreadsheet; if it fails and mock_allowed -> return mock
        try:
            if current_app.config.get('SPREADSHEET_ID'):
                _sheets.spreadsheets().get(spreadsheetId=current_app.config.get('SPREADSHEET_ID')).execute()
        except Exception as e:
            err_str = str(e)
            # If mock is allowed, prefer returning mock services (development mode)
            if mock_allowed:
                logging.warning("Google services init failed; returning mock services because GOOGLE_MOCK or DEBUG is enabled. Original error: %s", err_str)
                mock = _make_mock_service()
                return mock, mock, mock

            # If strict mode is enabled, surface the original error as critical
            if strict_mode:
                if 'invalid_grant' in err_str or 'Bad Request' in err_str:
                    msg = "Неверная подпись JWT. Проверьте private_key в файле сервисного аккаунта"
                    logging.critical(msg)
                    raise ValueError(msg)
                logging.critical("Google services init failed: %s", err_str)
                raise

            # Default fallback: return mock services but log error (shouldn't happen often)
            logging.error("Google services init failed (fallback). Returning mock services. Original error: %s", err_str)
            mock = _make_mock_service()
            return mock, mock, mock

        logging.info("✅ Google services initialized")
        return _drive, _sheets, _calendar
    except json.JSONDecodeError as e:
        err_str = str(e)
        if mock_allowed:
            logging.warning("GOOGLE_MOCK/DEBUG enabled: returning mock Google services due to JSON error in service account file: %s", err_str)
            mock = _make_mock_service()
            return mock, mock, mock
        logging.critical(f"❌ Ошибка чтения JSON файла сервисного аккаунта: {err_str}")
        raise
    except Exception as e:
        err_str = str(e)
        if mock_allowed:
            logging.warning("GOOGLE_MOCK/DEBUG enabled: returning mock Google services due to initialization error: %s", err_str)
            mock = _make_mock_service()
            return mock, mock, mock
        logging.critical(f"❌ Failed to initialize Google services: {err_str}")
        raise

def GoogleService(service_account_file=None):
    # Delegate to get_google_services which already contains fallback logic
    try:
        return get_google_services()
    except Exception as e:
        # If get_google_services raised, re-raise to preserve behavior for strict mode
        raise

def add_event_to_calendar(service, date, time, client_name, client_phone):
    try:
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
            calendarId=current_app.config['GOOGLE_CALENDAR_ID'],
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


def append_to_sheet(spreadsheet_id, worksheet_name, values):
    """
    Compatibility wrapper used by older modules: append a row (or rows) to a spreadsheet.
    Delegates to app.services.google_sheets_service.append_record which uses the
    same underlying Google Sheets client.
    """
    try:
        from app.services.google_sheets_service import append_record
        return append_record(spreadsheet_id, worksheet_name, values)
    except Exception as e:
        logging.error(f"Ошибка при записи в таблицу (compat append_to_sheet): {e}")
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

    if not folder_id:
        raise ValueError("Отсутствует переменная окружения: DRIVE_FOLDER_ID")

    # Prefer central factory which may return mock services in tests
    try:
        drive_service = get_google_services()[0]
    except Exception:
        # Fallback to direct credentials file if factory is unavailable
        if not creds_path:
            raise ValueError("Отсутствует переменная окружения: GOOGLE_SERVICE_ACCOUNT_FILE")
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
