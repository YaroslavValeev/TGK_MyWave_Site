import logging
from google.oauth2 import service_account
from googleapiclient.discovery import build
from datetime import datetime
import os
from app.services.google import get_google_services, reset_google_services
from app.config import (
    GOOGLE_SERVICE_ACCOUNT_FILE,
    SPREADSHEET_ID,
    GOOGLE_SHEET_NAME
)

# Настрой логирование
logger = logging.getLogger(__name__)


def _is_transient_google_transport_error(exc: BaseException) -> bool:
    """HttpError от googleapiclient при force_exception_to_status_code иногда кладёт SSL в content, а не в __str__."""
    chunks = [str(exc), repr(exc)]
    content = getattr(exc, "content", None)
    if isinstance(content, (bytes, bytearray)):
        try:
            chunks.append(content.decode("utf-8", errors="replace"))
        except Exception:
            chunks.append(str(content))
    s = " ".join(chunks).lower()
    markers = (
        "bad_record_mac",
        "decryption_failed",
        "sslerror",
        "ssl: ",
        "_ssl.c",
        "wrong version number",
        "connection reset",
        "broken pipe",
        "timed out",
        "timeout",
        "temporarily unavailable",
        "eof occurred",
    )
    return any(m in s for m in markers)


def _run_sheets_op_with_retry(label: str, fn):
    """Несколько попыток: сброс кэша Google-клиента между ними (TLS/httplib2 под eventlet)."""
    import time

    for attempt in range(3):
        try:
            return fn()
        except Exception as e:
            if not _is_transient_google_transport_error(e) or attempt >= 2:
                raise
            logger.warning(
                "%s: транспортная ошибка Google/SSL (попытка %s/3), сбрасываю HTTP-клиент: %s",
                label,
                attempt + 1,
                e,
            )
            reset_google_services()
            time.sleep(0.35)


def make_range(sheet_name, cell_range):
    if not sheet_name:
        return f"{cell_range}"
    # Escape single quotes inside sheet name by doubling them (Google Sheets syntax)
    safe = sheet_name.replace("'", "''")
    return f"'{safe}'!{cell_range}"

def get_sheets_service(credentials_file=None):
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file or GOOGLE_SERVICE_ACCOUNT_FILE, 
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
        range_name = make_range(worksheet_name, "A1:Z1000")
        logger.debug(f"Requesting range: {range_name} in sheet_id={sheet_id}")
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
        range_name = make_range(worksheet_name, "A1:Z1000")
        logger.debug(f"Appending to range: {range_name} in sheet_id={sheet_id}")
        body = {"values": [row_data]}
        service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body=body
        ).execute()
        logger.info(f"Данные успешно добавлены в таблицу {worksheet_name} (range={range_name})")
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

    def _read_impl():
        logger.info(f"\n{'='*50}\nЧТЕНИЕ GOOGLE SHEETS\n{'='*50}")
        logger.info(f"Spreadsheet ID: {spreadsheet_id or SPREADSHEET_ID}")
        logger.info(f"Worksheet: {worksheet_name or GOOGLE_SHEET_NAME}")

        sheets_service = get_google_services()[1]  # Получаем только sheets сервис
        logger.info("Sheets service получен успешно")

        # Сначала метаданные — чтобы имя листа совпало с таблицей (регистр / опечатки env)
        try:
            metadata = sheets_service.spreadsheets().get(
                spreadsheetId=spreadsheet_id or SPREADSHEET_ID
            ).execute()
            sheets = metadata.get('sheets', [])
            sheet_titles = [sheet['properties']['title'] for sheet in sheets]
            logger.info(f"Доступные листы: {', '.join(sheet_titles)}")

            resolved_ws = _resolve_worksheet_title(sheet_titles, worksheet_name or GOOGLE_SHEET_NAME)
            if resolved_ws not in sheet_titles:
                logger.error("Лист %r не найден в таблице (после сопоставления регистра)", worksheet_name)
                return []
        except Exception as e:
            logger.error(f"Ошибка при проверке метаданных таблицы: {e}")
            raise

        range_name = make_range(resolved_ws, "A1:Z1000")
        logger.info(f"Запрашиваем диапазон: {range_name}")

        # Теперь запрашиваем данные
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id or SPREADSHEET_ID,
            range=range_name
        ).execute()
        logger.info("Запрос к API выполнен успешно")

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

    try:
        return _run_sheets_op_with_retry("read_records", _read_impl)
    except Exception as e:
        logger.error(f"Ошибка чтения из Google Sheets: {e}")
        raise

def _resolve_worksheet_title(titles: list[str], requested: str) -> str:
    """Точное имя листа: учитываем регистр (Google различает, но дубликаты из-за env ломают create)."""
    if requested in titles:
        return requested
    by_lower = {t.lower(): t for t in titles}
    if requested.lower() in by_lower:
        resolved = by_lower[requested.lower()]
        if resolved != requested:
            logger.info(
                "Имя листа приведено к существующему в таблице: %r -> %r",
                requested,
                resolved,
            )
        return resolved
    return requested


def append_record(spreadsheet_id=None, worksheet_name=None, values=None):
    """Добавляет запись в Google Sheets. Создаёт лист при необходимости."""
    if values is None:
        raise ValueError("Значения для записи не указаны")

    def _append_impl():
        sheets_service = get_google_services()[1]
        sheet_id = spreadsheet_id or SPREADSHEET_ID
        sheet_name = worksheet_name or GOOGLE_SHEET_NAME

        titles: list[str] | None = None
        try:
            metadata = sheets_service.spreadsheets().get(spreadsheetId=sheet_id).execute()
            titles = [s["properties"]["title"] for s in metadata.get("sheets", [])]
        except Exception as e:
            logger.warning(
                "Не удалось получить метаданные таблицы (append_record): %s. "
                "Пропуск auto-create; запись с именем из конфига.",
                e,
            )
            titles = None

        actual_name = sheet_name
        if titles is not None:
            actual_name = _resolve_worksheet_title(titles, sheet_name)
            if actual_name not in titles:
                try:
                    logger.info("Лист %r не найден среди %s — создаю.", actual_name, titles[:12])
                    requests = [{"addSheet": {"properties": {"title": actual_name}}}]
                    sheets_service.spreadsheets().batchUpdate(
                        spreadsheetId=sheet_id, body={"requests": requests}
                    ).execute()
                    logger.info("Лист %r успешно создан", actual_name)
                except Exception as e:
                    logger.error(
                        "Не удалось создать лист %r: %s. Пробую append с этим именем.",
                        actual_name,
                        e,
                    )

        body = {
            'values': [values] if not isinstance(values[0], list) else values
        }
        range_name = make_range(actual_name, "A1")
        logger.debug(f"Appending record to range: {range_name} (sheet_id={sheet_id})")
        result = sheets_service.spreadsheets().values().append(
            spreadsheetId=sheet_id,
            range=range_name,
            valueInputOption='RAW',
            insertDataOption='INSERT_ROWS',
            body=body
        ).execute()
        return result

    try:
        return _run_sheets_op_with_retry("append_record", _append_impl)
    except Exception as e:
        logger.error(f"Ошибка добавления записи в Google Sheets: {e}")
        raise

def update_record(spreadsheet_id=None, worksheet_name=None, range_=None, values=None):
    """Обновляет запись в Google Sheets."""
    if values is None or range_ is None:
        raise ValueError("Не указаны значения или диапазон для обновления")

    def _update_impl():
        sheets_service = get_google_services()[1]
        body = {
            'values': [values] if not isinstance(values[0], list) else values
        }
        range_name = make_range((worksheet_name or GOOGLE_SHEET_NAME), range_)
        logger.debug(f"Updating range: {range_name}")
        result = sheets_service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id or SPREADSHEET_ID,
            range=range_name,
            valueInputOption='RAW',
            body=body
        ).execute()
        return result

    try:
        return _run_sheets_op_with_retry("update_record", _update_impl)
    except Exception as e:
        logger.error(f"Ошибка обновления записи в Google Sheets: {e}")
        raise


def log_analytics_event(payload: dict, spreadsheet_id: str = None, worksheet_name: str = None):
    """
    Записывает аналитическое событие в Google Sheets в стандартизированном формате.

    Формат строки (колонки):
      timestamp, event, context, user_key, rule_id, item_id, type, meta_json, ip, user_agent

    payload должен содержать хотя бы 'event'. Допустимые ключи: event, context, user_key,
    rule_id, item_id, type, meta (dict | str).
    """
    try:
        ts = datetime.utcnow().isoformat()
        event = payload.get('event', 'unknown')
        context = payload.get('context', '')
        user_key = payload.get('user_key', '')
        rule_id = payload.get('rule_id', '')
        item_id = payload.get('item_id', '')
        typ = payload.get('type', '')
        meta = payload.get('meta', '')
        # Ensure meta is JSON-string-ish
        try:
            import json
            meta_json = json.dumps(meta, ensure_ascii=False)
        except Exception:
            meta_json = str(meta)

        ip = payload.get('ip', '')
        ua = payload.get('user_agent', '')

        row = [ts, event, context, user_key, rule_id, item_id, typ, meta_json, ip, ua]

        sheet_id = spreadsheet_id or SPREADSHEET_ID
        sheet_name = worksheet_name or (os.environ.get('ANALYTICS_SHEET_NAME') or 'analytics_statistics')

        if not sheet_id:
            logger.warning('log_analytics_event: SPREADSHEET_ID not configured; skipping write')
            return False

        append_record(sheet_id, sheet_name, row)
        logger.info(f'Analytics event logged: {event} to {sheet_name}')
        return True
    except Exception as e:
        logger.error(f'Failed to log analytics event: {e}')
        return False
