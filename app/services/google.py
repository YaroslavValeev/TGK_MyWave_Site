import os
import json
import logging
from datetime import datetime, timedelta
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from google.oauth2.credentials import Credentials as OAuth2Credentials
from google_auth_oauthlib.flow import Flow
from flask import current_app
from googleapiclient.http import MediaIoBaseUpload
import io
SPREADSHEET_ID = os.environ.get("SPREADSHEET_ID")


logger = logging.getLogger(__name__)

class GoogleService:
    def __init__(self, service_account_file=None):
        try:
            if not service_account_file:
                service_account_file = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")

            if not service_account_file or not os.path.exists(service_account_file):
                raise FileNotFoundError(f"Файл сервисного аккаунта не найден: {service_account_file}")

            with open(service_account_file, 'r', encoding='utf-8') as file:
                service_account_info = json.load(file)

            SCOPES = [
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/calendar"
            ]

            self.creds = Credentials.from_service_account_info(
                service_account_info,
                scopes=SCOPES
            )

            self.drive_service = build("drive", "v3", credentials=self.creds)
            self.sheet_service = build("sheets", "v4", credentials=self.creds)
            self.calendar_service = build("calendar", "v3", credentials=self.creds)
            
            logger.info("✅ Google API успешно инициализирован!")

        except json.JSONDecodeError as e:
            logger.critical(f"❌ Ошибка чтения JSON файла сервисного аккаунта: {str(e)}")
            raise
        except Exception as e:
            logger.critical(f"❌ Ошибка инициализации сервисов Google: {str(e)}")
            raise

    def add_event_to_calendar(self, date, time, client_name, client_phone):
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

            self.calendar_service.events().insert(
                calendarId=current_app.config['GOOGLE_CALENDAR_ID'],
                body=event_body
            ).execute()

            logger.info('✅ Запись успешно добавлена в календарь')
            return True

        except Exception as e:
            logger.error(f'❌ Ошибка добавления события в календарь: {e}')
            return False

    def append_to_sheet(self, spreadsheet_id, range_name, values):
        try:
            self.sheet_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": values}
            ).execute()
        except Exception as e:
            logger.error("Ошибка добавления данных в таблицу: %s", str(e))
            raise

    def upload_to_drive(self, file_obj, user_id, folder_id):
        try:
            file_obj.seek(0)
            file_metadata = {
                "name": f"{user_id}_{file_obj.filename}",
                "parents": [folder_id]
            }
            media = MediaIoBaseUpload(file_obj.stream, mimetype=file_obj.content_type, resumable=True)
            uploaded_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink"
            ).execute()
            logger.info("Файл успешно загружен: %s", uploaded_file.get("id"))
            file_id = uploaded_file.get("id")
            webViewLink = uploaded_file.get("webViewLink", self.create_drive_link(file_id))
            return file_id, webViewLink
        except Exception as e:
            logger.error("Ошибка загрузки файла на Google Drive: %s", str(e))
            raise

    def list_user_files(self, folder_id, user_id):
        try:
            query = f"'{folder_id}' in parents and trashed=false and name contains '{user_id}_'"
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name, webViewLink)"
            ).execute()
            files = results.get("files", [])
            logger.info("Найдено файлов для пользователя %s: %d", user_id, len(files))
            return files
        except Exception as e:
            logger.error("Ошибка получения списка файлов: %s", str(e))
            raise

    def create_drive_link(self, file_id):
        """
        Creates a shareable Google Drive link for the given file ID
        
        Args:
            file_id (str): Google Drive file ID
            
        Returns:
            str: Shareable Google Drive link
        """
        try:
            link = f"https://drive.google.com/file/d/{file_id}/view"
            logger.info("Создана ссылка для файла: %s", link)
            return link
        except Exception as e:
            logger.error("Ошибка создания ссылки для файла: %s", str(e))
            raise

    def get_available_slots(self, start_date, end_date):
        try:
            # Get events from calendar
            events_result = self.calendar_service.events().list(
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
            logger.error(f'❌ Ошибка получения доступных слотов: {e}')
            return {}

    def upload_file_to_drive(self, file_content: bytes, filename: str):
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

def init_google_services(service_account_file=None):
    """
    Initialize Google services required for the application
    Args:
        service_account_file (str): Path to the service account credentials file
    Returns:
        tuple: (drive_service, sheet_service, calendar_service)
    """
    try:
        google_service = GoogleService(service_account_file)
        return (
            google_service.drive_service,
            google_service.sheet_service,
            google_service.calendar_service
        )
    except Exception as e:
        logger.critical(f"Failed to initialize Google services: {str(e)}")
        raise

def get_google_services():
    credentials = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"]
    )
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    return credentials, spreadsheet_id

def get_sheet_records(spreadsheet_id, sheet_name):
    try:
        service = get_google_services()
        sheet = service["sheets"]
        range_name = f"{sheet_name}!A1:Z1000"

        result = sheet.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()

        values = result.get("values", [])
        if not values:
            return [], []

        headers = values[0]
        records = []
        for row in values[1:]:
            record = {headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))}
            records.append(record)

        return records, headers
    except Exception as e:
        logging.error(f"❌ Ошибка при получении данных из таблицы '{sheet_name}': {str(e)}")
        return [], []

def append_to_sheet(sheets_service, spreadsheet_id, range_name, values):
    """
    Добавляет данные в указанный диапазон Google Sheets.
    :param sheets_service: объект сервиса sheets
    :param spreadsheet_id: ID таблицы
    :param range_name: строка диапазона (например, 'Clients!A2:I')
    :param values: список списков (2D-массив) значений
    """
    body = {
        'values': values
    }
    response = sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()
    return response
