import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
import logging
from flask import current_app
from app.modules.logger import logger
from app.services.google_sheets_service import (
    read_records,
    append_record,
    update_record,
)


def get_google_client():
    credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS")
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file
    )
    return build("sheets", "v4", credentials=credentials)


def get_sheets_service():
    credentials_file = os.getenv("GOOGLE_SHEETS_CREDENTIALS")

    if not credentials_file:
        raise ValueError("⚠️ Переменная среды GOOGLE_SHEETS_CREDENTIALS не задана.")

    credentials = service_account.Credentials.from_service_account_file(
        credentials_file,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ],
    )

    service = build("sheets", "v4", credentials=credentials)
    return service


def get_google_sheet(sheet_name):
    try:
        service = get_sheets_service()
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        sheet = (
            service.spreadsheets()
            .values()
            .get(
                spreadsheetId=spreadsheet_id,
                range=sheet_name,
            )
            .execute(num_retries=2)
        )  # 🛡️ повтор + тайм-аут

        values = sheet.get("values", [])
        if not values:
            return None
        return SheetWrapper(values)

    except Exception as e:
        current_app.logger.error(f"Ошибка получения данных из листа {sheet_name}: {e}")
        raise RuntimeError(f"Ошибка получения данных из листа {sheet_name}: {e}")


def get_sheet_records(sheet_name, range_):
    try:
        return read_records(sheet_name, range_)
    except Exception as e:
        logger.error(
            f"Ошибка при чтении из Google Sheets ({sheet_name}!{range_}): {e}",
            exc_info=True,
        )
        return []


def append_to_sheet(sheet_name, row):
    try:
        append_record(sheet_name, row)
    except Exception as e:
        logger.error(
            f"Ошибка при добавлении строки в Google Sheets ({sheet_name}): {e}",
            exc_info=True,
        )
        raise


def update_sheet_row(sheet_name, row_id, row):
    try:
        update_record(sheet_name, row_id, row)
    except Exception as e:
        logger.error(
            f"Ошибка при обновлении строки в Google Sheets ({sheet_name}, row {row_id}): {e}",
            exc_info=True,
        )
        raise


def append_dict_to_sheet(sheet_name, data_dict):
    """
    Универсальная функция для записи словаря в лист Google Sheets по актуальным заголовкам.
    :param sheet_name: имя листа (например, 'Clients')
    :param data_dict: словарь с данными для записи
    """
    try:
        sheet = get_google_sheet(sheet_name)
        headers = sheet.values[0]
    except Exception as e:
        logger.error(f"[ERROR] Не удалось получить заголовки {sheet_name}: {e}")
        raise
    row = [data_dict.get(header, "") for header in headers]
    logger.error(f"[DEBUG] Заголовки {sheet_name}: {headers}")
    logger.error(f"[DEBUG] Формируемые значения для записи: {row}")
    append_record(current_app.config["SPREADSHEET_ID"], sheet_name, row)


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
        for idx, row in enumerate(
            all_records, start=2
        ):  # начиная со 2 строки, т.к. первая — заголовки
            if all(row.get(key) == value for key, value in kwargs.items()):
                result.append((idx, row))
        return result
