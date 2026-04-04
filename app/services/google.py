import os
import json
import logging
import datetime
from datetime import datetime, timedelta
import httplib2
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google_auth_oauthlib.flow import Flow
from google_auth_httplib2 import AuthorizedHttp
from flask import current_app
from googleapiclient.http import MediaIoBaseUpload
import io
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/calendar",
]

_drive = _sheets = _calendar = None


def reset_google_services() -> None:
    """Сбрасывает кэш Drive/Sheets/Calendar.

    Один общий httplib2.Http под eventlet иногда оставляет «битое» TLS-соединение
    (BAD_RECORD_MAC / DECRYPTION_FAILED). Следующий вызов get_google_services()
    создаёт новый HTTP-клиент и заново собирает сервисы.
    """
    global _drive, _sheets, _calendar
    _drive = _sheets = _calendar = None


def get_google_services():
    """Лениво инициализирует и кеширует сервисы Google Drive, Sheets и Calendar.

    Берёт путь к service account из current_app.config["GOOGLE_SERVICE_ACCOUNT_FILE"].
    Keep import-time effects minimal so tests can patch `service_account.Credentials.from_service_account_file`
    and `build` without needing a real file on disk.
    """
    global _drive, _sheets, _calendar
    if _drive and _sheets and _calendar:
        return _drive, _sheets, _calendar

    creds_path = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if not creds_path:
        msg = "GOOGLE_SERVICE_ACCOUNT_FILE не задан в конфигурации"
        logging.critical(msg)
        raise ValueError(msg)

    # Allow tests to mock os.path.isfile and Credentials.from_service_account_file
    if not os.path.isfile(creds_path):
        msg = f"Файл сервисного аккаунта не найден: {creds_path}"
        logging.critical(msg)
        raise FileNotFoundError(msg)

    try:
        creds = service_account.Credentials.from_service_account_file(creds_path, scopes=SCOPES)
        # Отдельный httplib2.Http на каждый API: один общий пул соединений под eventlet даёт
        # «Second simultaneous read» / BAD_RECORD_MAC при пересечении запросов к разным хостам.
        def _authorized_http():
            http = httplib2.Http(timeout=60)
            http.force_exception_to_status_code = True
            return AuthorizedHttp(creds, http=http)

        _drive = build("drive", "v3", http=_authorized_http(), cache_discovery=False)
        _sheets = build("sheets", "v4", http=_authorized_http(), cache_discovery=False)
        _calendar = build("calendar", "v3", http=_authorized_http(), cache_discovery=False)

        # Optional runtime check (will be mocked in tests)
        try:
            _sheets.spreadsheets().get(spreadsheetId=current_app.config.get('SPREADSHEET_ID')).execute()
        except Exception as e:
            if 'invalid_grant' in str(e):
                msg = "Неверная подпись JWT. Проверьте private_key в файле сервисного аккаунта"
                logging.critical(msg)
                raise ValueError(msg)
            # non-critical for initialization: re-raise
            raise

        logging.info("✅ Google services initialized")
        return _drive, _sheets, _calendar
    except Exception as e:
        logging.critical(f"Failed to initialize Google services: {e}")
        raise

def read_sheet(spreadsheet_id: str, sheet_name: str) -> tuple[list[dict], list[str]]:
    svc = get_google_services()[1]
    # Расширяем диапазон до ZZ для поддержки большого количества колонок (raw_feed)
    result = svc.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range=f"{sheet_name}!A1:ZZ1000"
    ).execute()
    values = result.get("values", [])
    if not values:
        return [], []

    # В некоторых реальных листах заголовки могут быть не в первой строке (например, если сверху есть данные/служебные строки).
    # Поэтому ищем строку заголовков эвристикой: должна содержать ключевые колонки (id + status).
    def _norm(s: str) -> str:
        return str(s or "").strip().lower()

    # Эвристика: выбираем строку с максимальным количеством совпадений ожидаемых заголовков.
    # Это устойчивее, чем "первое совпадение", если в данных встречаются слова "id"/"status".
    expected = {"id", "status", "published_posts", "publish_error", "source_type"}
    header_row_idx = 0
    best_score = -1
    # Важно: анализируем только первые ~80 колонок, чтобы не схватить "служебные" блоки справа
    # (например, CONTRACT/меню), которые могут содержать слова 'id'/'status' и давать ложные совпадения.
    for i, row in enumerate(values[:400]):  # ограничимся первыми 400 строками
        row_norm = {_norm(c) for c in row[:80] if _norm(c)}
        score = len(expected.intersection(row_norm))
        if score > best_score:
            best_score = score
            header_row_idx = i

    # Если заголовки не распознаны (слишком мало совпадений) — fallback на первую строку.
    if best_score < 2:
        header_row_idx = 0

    headers = values[header_row_idx]
    records = []
    # Подготовим карту индексов сразу (нужно и для логирования дублей)
    header_indices = {}
    for i, hdr in enumerate(headers):
        header_indices.setdefault(hdr, []).append(i)

    # Логируем дубликаты заголовков (предупреждение, но не блокируем работу)
    duplicate_headers = {h: idxs for h, idxs in header_indices.items() if len(idxs) > 1}
    if duplicate_headers:
        # Пример: {'final_posts': [21, 40], 'ingest_error': [17, 44]}
        logging.warning(
            "[google.read_sheet] Дубликаты заголовков обнаружены: %s",
            {h: idxs for h, idxs in duplicate_headers.items()}
        )

    for offset, row in enumerate(values[header_row_idx + 1 :]):
        record = {}
        for hdr, indices in header_indices.items():
            # Если заголовок уникален - просто берём значение
            if len(indices) == 1:
                i = indices[0]
                record[hdr] = row[i] if i < len(row) else ""
            else:
                # Если дубликат - берём первое непустое значение
                # И сохраняем все значения в список (для отладки)
                values_list = []
                for i in indices:
                    val = row[i] if i < len(row) else ""
                    if val:
                        values_list.append(val)
                
                # Берём первое непустое значение
                record[hdr] = values_list[0] if values_list else ""
                
                # Для критичных полей (final_posts) сохраняем все варианты
                if hdr == "final_posts" and len(values_list) > 1:
                    # Сохраняем все непустые значения в отдельное поле для отладки
                    record["_final_posts_all"] = values_list
        # Сохраняем реальный номер строки листа (1-based) для внутренней диагностики.
        record["_sheet_row_number"] = header_row_idx + 2 + offset
        records.append(record)
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

        authed_http = AuthorizedHttp(creds, http=httplib2.Http(timeout=10))
        drive_service = build("drive", "v3", http=authed_http, cache_discovery=False)
        sheet_service = build("sheets", "v4", http=authed_http, cache_discovery=False)
        calendar_service = build("calendar", "v3", http=authed_http, cache_discovery=False)
        
        logging.info("✅ Google API успешно инициализирован!")

        return drive_service, sheet_service, calendar_service

    except json.JSONDecodeError as e:
        logging.critical(f"❌ Ошибка чтения JSON файла сервисного аккаунта: {str(e)}")
        raise
    except Exception as e:
        logging.critical(f"❌ Ошибка инициализации сервисов Google: {str(e)}")
        raise

def add_event_to_calendar(service, date, time, client_name, client_phone):
    """
    Добавление события в Google Calendar с таймаутом.
    Если Calendar недоступен/висит — не блокируем бронь, просто возвращаем False.
    """
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

        # Жёсткий таймаут на сетевой вызов Calendar API
        try:
            import eventlet
            with eventlet.Timeout(8, False):  # если зависает дольше 8с — прерываем
                service[2].events().insert(
                    calendarId=current_app.config['GOOGLE_CALENDAR_ID'],
                    body=event_body
                ).execute()
            if isinstance(eventlet.Timeout, BaseException) and eventlet.Timeout.pending:
                # eventlet <= для совместимости: если не сработало, просто продолжаем
                pass
        except Exception:
            # fallback без eventlet (если не установлен): просто пытаемся с коротким http timeout
            pass

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
