import os
import logging
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from flask import current_app
from googleapiclient.http import MediaIoBaseUpload

logger = logging.getLogger(__name__)

def init_google_services(service_account_file=None):
    try:
        # Проверяем, передан ли путь через аргумент, иначе берём из Flask-конфигурации
        if not service_account_file:
            service_account_file = current_app.config.get("GOOGLE_SERVICE_ACCOUNT_FILE")

        if not service_account_file or not os.path.exists(service_account_file):
            raise FileNotFoundError(f"Файл сервисного аккаунта не найден: {service_account_file}")

        # Загружаем учетные данные
        creds = Credentials.from_service_account_file(
            service_account_file,
            scopes=[
                "https://www.googleapis.com/auth/drive.file",
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/calendar"
            ]
        )

        # Инициализация сервисов Google API
        drive_service = build("drive", "v3", credentials=creds)
        sheet_service = build("sheets", "v4", credentials=creds)
        calendar_service = build("calendar", "v3", credentials=creds)

        logger.info("✅ Google API успешно инициализирован!")
        return drive_service, sheet_service, calendar_service

    except Exception as e:
        logger.critical(f"❌ Ошибка инициализации сервисов Google: {str(e)}")
        return None, None, None
    
def append_to_sheet(sheet_service, spreadsheet_id, range_name, values):
    try:
        sheet_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption="RAW",
            body={"values": values}
        ).execute()
    except Exception as e:
        logger.error("Ошибка добавления данных в таблицу: %s", str(e))
        raise

def upload_to_drive(drive_service, file_obj, user_id, folder_id):
    try:
        file_obj.seek(0)
        file_metadata = {
            "name": f"{user_id}_{file_obj.filename}",
            "parents": [folder_id]
        }
        media = MediaIoBaseUpload(file_obj.stream, mimetype=file_obj.content_type, resumable=True)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink"
        ).execute()
        logger.info("Файл успешно загружен: %s", uploaded_file.get("id"))
        file_id = uploaded_file.get("id")
        webViewLink = uploaded_file.get("webViewLink", create_drive_link(file_id))
        return file_id, webViewLink
    except Exception as e:
        logger.error("Ошибка загрузки файла на Google Drive: %s", str(e))
        raise

def list_user_files(drive_service, folder_id, user_id):
    try:
        query = f"'{folder_id}' in parents and trashed=false and name contains '{user_id}_'"
        results = drive_service.files().list(
            q=query,
            fields="files(id, name, webViewLink)"
        ).execute()
        files = results.get("files", [])
        logger.info("Найдено файлов для пользователя %s: %d", user_id, len(files))
        return files
    except Exception as e:
        logger.error("Ошибка получения списка файлов: %s", str(e))
        raise

def create_drive_link(file_id):
    try:
        link = f"https://drive.google.com/file/d/{file_id}/view"
        logger.info("Создана ссылка для файла: %s", link)
        return link
    except Exception as e:
        logger.error("Ошибка создания ссылки для файла: %s", str(e))
        raise
