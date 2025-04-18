import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging
from flask import current_app
from app.services.google import SPREADSHEET_ID

def get_google_client():
    credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    credentials = service_account.Credentials.from_service_account_file(credentials_file)
    return build('sheets', 'v4', credentials=credentials)

def get_sheets_service():
    credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    
    if not credentials_file:
        raise ValueError("⚠️ Переменная среды GOOGLE_SHEETS_CREDENTIALS не задана.")
    
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=['https://www.googleapis.com/auth/spreadsheets', 'https://www.googleapis.com/auth/drive']
    )
    
    service = build('sheets', 'v4', credentials=credentials)
    return service

def get_google_sheet(sheet_name):
    try:
        service = get_sheets_service()
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        sheet = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=sheet_name,
        ).execute(num_retries=2)  # 🛡️ повтор + тайм-аут

        values = sheet.get("values", [])
        if not values:
            return None
        return SheetWrapper(values)

    except Exception as e:
        current_app.logger.error(f"Ошибка получения данных из листа {sheet_name}: {e}")
        raise RuntimeError(f"Ошибка получения данных из листа {sheet_name}: {e}")



def get_sheet_records(sheet_name):
    try:
        service = get_sheets_service()
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A1:Z1000"
        ).execute()
        values = result.get("values", [])
        if not values or len(values) < 2:
            return []
        headers = values[0]
        records = [dict(zip(headers, row)) for row in values[1:]]
        return records
    except Exception as e:
        logging.error(f"Ошибка получения данных из листа {sheet_name}: {e}")
        return []

def append_to_sheet(sheet_name, values):
    """
    Добавляет строку в указанный лист Google Sheets.
    """
    service = get_sheets_service()
    spreadsheet_id = current_app.config["SPREADSHEET_ID"]
    range_name = f"{sheet_name}!A1"
    body = {"values": [values]}

    service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range=range_name,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body
    ).execute()

class SheetWrapper:
    """
    Обёртка над значениями листа Google Sheets.
    Предоставляет методы get_all_records() и find_rows() для удобной работы.
    """
    def __init__(self, values):
        self.values = values

    def get_all_records(self):
        if not self.values:
            return []
        headers = self.values[0]
        records = []
        for row in self.values[1:]:
            record = dict(zip(headers, row))
            records.append(record)
        return records

    def find_rows(self, **kwargs):
        """
        Возвращает строки, соответствующие переданным параметрам в виде словаря: {column_name: value}
        Возвращает список кортежей (индекс_строки, строка-словарь).
        Индексация начинается со 2 строки (первая — заголовки).
        """
        result = []
        all_records = self.get_all_records()
        for idx, row in enumerate(all_records, start=2):  # начиная со 2 строки, т.к. первая — заголовки
            if all(row.get(key) == value for key, value in kwargs.items()):
                result.append((idx, row))
        return result
