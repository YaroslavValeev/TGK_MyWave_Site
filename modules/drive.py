# modules/drive.py
import os
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials

def get_drive_service():
    # Используем тот же файл учетных данных, что и для Sheets/Calendar
    creds = Credentials.from_service_account_file(
        os.getenv("GOOGLE_SHEETS_CREDENTIALS"),
        scopes=["https://www.googleapis.com/auth/drive.readonly"]
    )
    return build("drive", "v3", credentials=creds)

def list_media_files():
    service = get_drive_service()
    folder_id = os.getenv("DRIVE_FOLDER_ID")
    query = f"'{folder_id}' in parents and trashed=false"
    # Запрашиваем ID, имя и веб-ссылку для просмотра
    results = service.files().list(q=query, fields="files(id, name, webViewLink)").execute()
    files = results.get("files", [])
    return files
