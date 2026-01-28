"""
Модуль для публикации новостей с обратной записью в Google Sheets (ack).

Обеспечивает:
- Lock-механизм для предотвращения гонок
- Автоматическую публикацию записей со статусом READY_TO_PUBLISH
- Подтверждение публикации (ack) обратно в Sheets
"""
import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

from flask import current_app

from app.modules.logger import get_logger
from app.services.parser_news_sheet import resolve_parser_source, fetch_parser_news_rows
from app.services.google import read_sheet, get_google_services

logger = get_logger(__name__)


# === P0 contract (site-side) ===
# Источник истины — headers листа raw_feed. Ниже — минимальные ожидания сайта для безопасного writeback.

WP_SCHEMA_MISMATCH = "WP_SCHEMA_MISMATCH"
WP_ROW_NUMBER_MISSING = "WP_ROW_NUMBER_MISSING"
WP_ROW_NUMBER_INVALID = "WP_ROW_NUMBER_INVALID"
WP_ROW_NUMBER_AMBIGUOUS = "WP_ROW_NUMBER_AMBIGUOUS"

RAW_FEED_REQUIRED_WRITEBACK_COLUMNS: List[str] = [
    "row_number",
    "status",
    "published_posts",
    "published_at",
    "publish_attempts",
    "publish_last_try_at",
    "publish_error",
    "canonical_url",
]


def _norm_header(h: str) -> str:
    return str(h or "").strip().lower()


def _validate_required_columns(headers: List[str], required: List[str]) -> Tuple[bool, List[str]]:
    headers_lower = {_norm_header(h) for h in (headers or []) if _norm_header(h)}
    missing = [c for c in required if _norm_header(c) not in headers_lower]
    return (len(missing) == 0), missing


def _validate_row_number(raw_value: object) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Валидирует row_number из таблицы:
    - целое число
    - >= 2 (строка 1 — заголовок)
    Возвращает: (ok, value, error_code)
    """
    if raw_value is None:
        return False, None, WP_ROW_NUMBER_MISSING
    s = str(raw_value).strip()
    if s == "":
        return False, None, WP_ROW_NUMBER_MISSING
    try:
        n = int(s)
    except Exception:
        return False, None, WP_ROW_NUMBER_INVALID
    if n < 2:
        return False, None, WP_ROW_NUMBER_INVALID
    return True, n, None


def _get_lock_by_prefix() -> str:
    """Возвращает префикс для lock_by."""
    prefix = current_app.config.get("BLOG_PUBLISH_LOCK_BY_PREFIX", "site:mywave") if current_app else os.getenv("BLOG_PUBLISH_LOCK_BY_PREFIX", "site:mywave")
    # Можно добавить instance_id для уникальности
    return prefix


def _get_lock_ttl_minutes() -> int:
    """Возвращает TTL lock в минутах."""
    if current_app:
        ttl = current_app.config.get("BLOG_PUBLISH_LOCK_TTL_MINUTES", 5)
        return int(ttl) if ttl else 5
    return int(os.getenv("BLOG_PUBLISH_LOCK_TTL_MINUTES", "5"))


def _find_column_index(headers: List[str], column_name: str) -> Optional[int]:
    """Находит индекс колонки по названию (case-insensitive)."""
    column_name_lower = column_name.lower()
    for i, hdr in enumerate(headers):
        if hdr.lower() == column_name_lower:
            return i
    return None


def _is_test_row_index_fallback_enabled() -> bool:
    """
    Разрешает небезопасный fallback (index+2) ТОЛЬКО в тестовом режиме.
    На проде fallback запрещён: row_number обязан приходить из таблицы.
    """
    try:
        return bool(current_app and getattr(current_app, "testing", False))
    except Exception:
        return False


def _get_row_number_from_record(record: Dict, index_in_records: int) -> Optional[int]:
    """
    Получает номер строки для writeback.

    P0 правило:
    - Приоритет: row_number из таблицы (заполняет Parser Bot)
    - Валидация: int >= 2
    - Fallback index+2 допускается ТОЛЬКО в тестовом режиме (явно).
    """
    ok, n, code = _validate_row_number(record.get("row_number"))
    if ok:
        return n
    if _is_test_row_index_fallback_enabled():
        return index_in_records + 2
    return None


def _get_public_blog_base_url() -> str:
    """
    Базовый URL для canonical_url.
    Если в конфиге задан SERVER_NAME, используем его. Иначе fallback на основной домен проекта.
    """
    try:
        server_name = (current_app.config.get("SERVER_NAME") or "").strip() if current_app else ""
    except Exception:
        server_name = ""
    if server_name:
        return f"https://{server_name}".rstrip("/")
    return "https://mywavetraining.ru"


def _make_canonical_url(slug: str) -> Optional[str]:
    slug = str(slug or "").strip().lstrip("/")
    if not slug:
        return None
    base = _get_public_blog_base_url().rstrip("/")
    return f"{base}/blog/{slug}"


def _validate_writeback_schema(headers: List[str]) -> Tuple[bool, List[str]]:
    """P0: проверяем обязательные колонки перед любым writeback."""
    required = list(RAW_FEED_REQUIRED_WRITEBACK_COLUMNS)
    ok, missing = _validate_required_columns(headers, required)
    return ok, missing


def _safe_find_row_number_by_unique_id(
    spreadsheet_id: str,
    sheet_name: str,
    sheet_id: str,
    logger=None,
) -> Tuple[Optional[int], Optional[str]]:
    """
    Безопасный поиск номера строки по sheet_id (если row_number пуст/невалиден).

    Используем только для записи publish_error (и диагностики), чтобы не писать «в чужую строку».
    Правило безопасности: ID должен совпасть РОВНО с одной строкой.
    """
    if logger is None:
        logger = get_logger(__name__)
    try:
        records, _headers = read_sheet(spreadsheet_id, sheet_name)
    except Exception as e:
        logger.error(f"[blog-publish] Не удалось перечитать лист для поиска строки по id: {e}", exc_info=True)
        return None, None

    matches: List[int] = []
    for i, r in enumerate(records):
        rid = str(r.get("id") or r.get("news_id") or r.get("raw_id") or "").strip()
        if rid and rid == sheet_id:
            matches.append(i)

    if len(matches) == 1:
        r = records[matches[0]]
        # Если адаптер чтения проставил реальный номер строки — используем его.
        try:
            srn = int(str(r.get("_sheet_row_number") or "").strip())
            if srn >= 2:
                return srn, None
        except Exception:
            pass
        # Fallback (на случай старого формата records): индекс + заголовок
        return matches[0] + 2, None
    if len(matches) == 0:
        return None, WP_ROW_NUMBER_MISSING
    return None, WP_ROW_NUMBER_AMBIGUOUS


def _find_record_by_row_number(records: List[Dict], row_number: int) -> Optional[Dict]:
    """Находит запись по совпадению record['row_number'] == row_number."""
    for r in records or []:
        try:
            rn = int(str(r.get("row_number") or "").strip())
        except Exception:
            rn = None
        if rn == row_number:
            return r
    return None


def _find_record_by_sheet_row_number(records: List[Dict], sheet_row_number: int) -> Optional[Dict]:
    """
    Находит запись по внутреннему полю _sheet_row_number (реальный номер строки листа).
    Поле приходит из адаптера чтения Sheets (`app/services/google.py::read_sheet`).
    """
    for r in records or []:
        try:
            srn = int(str(r.get("_sheet_row_number") or "").strip())
        except Exception:
            srn = None
        if srn == sheet_row_number:
            return r
    return None


def update_sheet_cells(spreadsheet_id: str, sheet_name: str, updates: List[Dict[str, Any]]) -> bool:
    """
    Обновляет несколько ячеек в Sheets через batch update.
    
    Args:
        spreadsheet_id: ID таблицы
        sheet_name: Название листа
        updates: список словарей {"range": "A1", "values": [["value"]]}
    
    Returns:
        True при успехе, False при ошибке
    """
    try:
        svc = get_google_services()[1]
        
        data = []
        for update in updates:
            if "range" not in update or "values" not in update:
                continue
            data.append({
                "range": f"{sheet_name}!{update['range']}",
                "values": update["values"]
            })
        
        if not data:
            return False
        
        body = {
            "valueInputOption": "RAW",
            "data": data
        }
        
        svc.spreadsheets().values().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body=body
        ).execute()
        
        return True
    except Exception as e:
        logger.error(f"[blog-publish] Ошибка batch update в Sheets: {e}", exc_info=True)
        return False


def acquire_publish_lock(row_number: int, lock_ttl_minutes: Optional[int] = None, logger=None) -> bool:
    """
    Пытается получить lock для публикации строки.
    
    Args:
        row_number: Номер строки в Sheets
        lock_ttl_minutes: TTL lock в минутах (по умолчанию из конфига)
        logger: Логгер (опционально)
    
    Returns:
        True если lock получен, False если уже занят или ошибка
    """
    if logger is None:
        logger = get_logger(__name__)
    
    try:
        spreadsheet_id, sheet_name = resolve_parser_source()
        lock_ttl = lock_ttl_minutes or _get_lock_ttl_minutes()
        lock_by = _get_lock_by_prefix()
        
        # Читаем текущие значения lock
        records, headers = read_sheet(spreadsheet_id, sheet_name)
        
        # P0: работаем только по row_number из таблицы. Не опираемся на индекс records[row_number-2],
        # т.к. заголовки могут быть не в A1.
        if row_number < 2:
            logger.warning(f"[blog-publish] Некорректный row_number для lock: {row_number}")
            return False

        record = _find_record_by_row_number(records, row_number)
        if record is None:
            logger.warning(f"[blog-publish] Не найдена запись с row_number={row_number} для lock")
            return False
        
        # Проверяем текущий lock
        lock_by_col = _find_column_index(headers, "publish_lock_by")
        lock_until_col = _find_column_index(headers, "publish_lock_until")
        
        if lock_by_col is not None and lock_until_col is not None:
            current_lock_by = str(record.get(headers[lock_by_col]) or "").strip()
            current_lock_until = str(record.get(headers[lock_until_col]) or "").strip()
            
            # Проверяем, не занят ли lock
            if current_lock_until:
                try:
                    lock_until_dt = datetime.fromisoformat(current_lock_until.replace("Z", "+00:00"))
                    now = datetime.utcnow()
                    if lock_until_dt > now and current_lock_by and current_lock_by != lock_by:
                        logger.debug(f"[blog-publish] Lock занят для строки {row_number} (by: {current_lock_by})")
                        return False
                except Exception:
                    # Если не удалось распарсить дату, считаем lock свободным
                    pass
        
        # Устанавливаем lock
        lock_until = (datetime.utcnow() + timedelta(minutes=lock_ttl)).isoformat() + "Z"
        
        updates = []
        if lock_by_col is not None:
            # Получаем букву колонки (A, B, C, ...)
            col_letter = _column_index_to_letter(lock_by_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[lock_by]]
            })
        
        if lock_until_col is not None:
            col_letter = _column_index_to_letter(lock_until_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[lock_until]]
            })
        
        if not updates:
            logger.warning(f"[blog-publish] Колонки lock не найдены в Sheets")
            return False
        
        success = update_sheet_cells(spreadsheet_id, sheet_name, updates)
        if success:
            logger.debug(f"[blog-publish] Lock получен для строки {row_number}")
        return success
        
    except Exception as e:
        logger.error(f"[blog-publish] Ошибка при получении lock для строки {row_number}: {e}", exc_info=True)
        return False


def _column_index_to_letter(n: int) -> str:
    """Конвертирует индекс колонки (0-based) в букву (A, B, C, ..., Z, AA, AB, ...)."""
    result = ""
    n += 1  # Переводим в 1-based
    while n > 0:
        n -= 1
        result = chr(65 + (n % 26)) + result
        n //= 26
    return result


def release_publish_lock(row_number: int, logger=None) -> None:
    """
    Снимает lock для публикации строки.
    
    Args:
        row_number: Номер строки в Sheets
        logger: Логгер (опционально)
    """
    if logger is None:
        logger = get_logger(__name__)
    
    try:
        spreadsheet_id, sheet_name = resolve_parser_source()
        
        records, headers = read_sheet(spreadsheet_id, sheet_name)
        if row_number < 2:
            return
        # Если строка отсутствует — ничего не делаем (безопасно)
        if _find_record_by_row_number(records, row_number) is None:
            return
        
        lock_by_col = _find_column_index(headers, "publish_lock_by")
        lock_until_col = _find_column_index(headers, "publish_lock_until")
        
        updates = []
        if lock_by_col is not None:
            col_letter = _column_index_to_letter(lock_by_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[""]]
            })
        
        if lock_until_col is not None:
            col_letter = _column_index_to_letter(lock_until_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[""]]
            })
        
        if updates:
            update_sheet_cells(spreadsheet_id, sheet_name, updates)
            logger.debug(f"[blog-publish] Lock снят для строки {row_number}")
            
    except Exception as e:
        logger.error(f"[blog-publish] Ошибка при снятии lock для строки {row_number}: {e}", exc_info=True)


def ack_publish(row_number: int, sheet_id: str, published_at: datetime, slug: Optional[str] = None, logger=None) -> bool:
    """
    Подтверждает успешную публикацию (ack).
    
    Обновляет в Sheets:
    - published_posts = TRUE
    - published_at = <timestamp>
    - canonical_url = <base_url>/blog/<slug> (если slug доступен)
    - publish_error = (очистить)
    - publish_last_try_at = <timestamp>
    - publish_lock_by = (очистить)
    - publish_lock_until = (очистить)
    
    Ownership (P0): сайт НЕ пишет ingest/process/parse поля и по умолчанию НЕ трогает slug/status.
    
    Args:
        row_number: Номер строки в Sheets
        sheet_id: ID записи (для проверки)
        published_at: Дата публикации
        slug: URL-слаг (опционально)
        logger: Логгер (опционально)
    
    Returns:
        True при успехе, False при ошибке
    """
    if logger is None:
        logger = get_logger(__name__)
    
    try:
        spreadsheet_id, sheet_name = resolve_parser_source()
        
        # Читаем заголовки для определения индексов колонок
        records, headers = read_sheet(spreadsheet_id, sheet_name)

        # P0: валидируем схему перед writeback
        schema_ok, missing_cols = _validate_writeback_schema(headers)
        if not schema_ok:
            logger.warning(f"[blog-publish] Несовпадение схемы Sheets (ack): missing={missing_cols}")
            # Пытаемся записать WP_SCHEMA_MISMATCH (если publish_error колонка существует)
            error_col = _find_column_index(headers, "publish_error")
            if error_col is not None:
                col_letter = _column_index_to_letter(error_col)
                update_sheet_cells(
                    spreadsheet_id,
                    sheet_name,
                    [{"range": f"{col_letter}{row_number}", "values": [[WP_SCHEMA_MISMATCH]]}],
                )
            return False
        
        if row_number < 2:
            logger.warning(f"[blog-publish] Некорректный row_number для ack: {row_number}")
            return False

        record = _find_record_by_row_number(records, row_number)
        if record is None:
            logger.warning(f"[blog-publish] Не найдена запись с row_number={row_number} для ack")
            return False
        
        # Проверяем, что это правильная запись
        id_col = _find_column_index(headers, "id")
        if id_col is not None:
            record_id = str(record.get(headers[id_col]) or "").strip()
            if record_id != sheet_id:
                logger.warning(f"[blog-publish] ID не совпадает: ожидали {sheet_id}, получили {record_id}")
                return False
        
        # Подготавливаем обновления
        updates = []
        published_at_str = published_at.isoformat() + "Z"
        
        # Находим индексы колонок
        published_posts_col = _find_column_index(headers, "published_posts")
        published_at_col = _find_column_index(headers, "published_at")
        publish_error_col = _find_column_index(headers, "publish_error")
        attempts_col = _find_column_index(headers, "publish_attempts")
        last_try_col = _find_column_index(headers, "publish_last_try_at")
        lock_by_col = _find_column_index(headers, "publish_lock_by")
        lock_until_col = _find_column_index(headers, "publish_lock_until")
        canonical_url_col = _find_column_index(headers, "canonical_url")
        slug_col = _find_column_index(headers, "slug")
        
        # published_posts = TRUE
        if published_posts_col is not None:
            col_letter = _column_index_to_letter(published_posts_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [["TRUE"]]
            })
        
        # published_at
        if published_at_col is not None:
            col_letter = _column_index_to_letter(published_at_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[published_at_str]]
            })

        # publish_attempts (site-owned): считаем попыткой и успешный ack
        if attempts_col is not None:
            current_attempts = 0
            try:
                current_attempts = int(str(record.get(headers[attempts_col]) or "0").strip() or 0)
            except Exception:
                current_attempts = 0
            col_letter = _column_index_to_letter(attempts_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[str(current_attempts + 1)]]
            })

        # publish_last_try_at (фиксируем успешную попытку)
        if last_try_col is not None:
            col_letter = _column_index_to_letter(last_try_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[published_at_str]]
            })
        
        # Очищаем publish_error
        if publish_error_col is not None:
            col_letter = _column_index_to_letter(publish_error_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[""]]
            })
        
        # Снимаем lock
        if lock_by_col is not None:
            col_letter = _column_index_to_letter(lock_by_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[""]]
            })
        
        if lock_until_col is not None:
            col_letter = _column_index_to_letter(lock_until_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[""]]
            })

        # canonical_url (site-owned)
        if canonical_url_col is not None:
            sheet_slug = str(record.get(headers[slug_col]) or "").strip() if slug_col is not None else ""
            effective_slug = sheet_slug or str(slug or "").strip()
            canonical_url = _make_canonical_url(effective_slug)
            if canonical_url:
                col_letter = _column_index_to_letter(canonical_url_col)
                updates.append({
                    "range": f"{col_letter}{row_number}",
                    "values": [[canonical_url]]
                })
        
        if not updates:
            logger.warning(f"[blog-publish] Не найдены колонки для ack")
            return False
        
        success = update_sheet_cells(spreadsheet_id, sheet_name, updates)
        if success:
            logger.info(f"[blog-publish] Ack отправлен для строки {row_number} (id: {sheet_id})")
        return success
        
    except Exception as e:
        logger.error(f"[blog-publish] Ошибка при отправке ack для строки {row_number}: {e}", exc_info=True)
        return False


def record_publish_error(row_number: int, error_msg: str, increment_attempts: bool = True, logger=None) -> None:
    """
    Записывает ошибку публикации в Sheets.
    
    Args:
        row_number: Номер строки в Sheets
        error_msg: Сообщение об ошибке
        increment_attempts: Инкрементировать publish_attempts
        logger: Логгер (опционально)
    """
    if logger is None:
        logger = get_logger(__name__)
    
    try:
        if row_number < 2:
            return
        spreadsheet_id, sheet_name = resolve_parser_source()
        
        records, headers = read_sheet(spreadsheet_id, sheet_name)

        # P0: валидируем схему перед writeback (как минимум publish_* и canonical_url должны быть известны)
        schema_ok, missing_cols = _validate_writeback_schema(headers)
        if not schema_ok:
            logger.warning(f"[blog-publish] Несовпадение схемы Sheets (error write): missing={missing_cols}")
            # Если publish_error есть — попробуем записать WP_SCHEMA_MISMATCH (без инкремента attempts)
            error_col = _find_column_index(headers, "publish_error")
            if error_col is not None and row_number <= len(records) + 1:
                col_letter = _column_index_to_letter(error_col)
                update_sheet_cells(
                    spreadsheet_id,
                    sheet_name,
                    [{"range": f"{col_letter}{row_number}", "values": [[WP_SCHEMA_MISMATCH]]}],
                )
            return
        
        record = _find_record_by_row_number(records, row_number) or _find_record_by_sheet_row_number(records, row_number)
        if record is None:
            return
        
        updates = []
        now_str = datetime.utcnow().isoformat() + "Z"
        
        # Записываем ошибку
        error_col = _find_column_index(headers, "publish_error")
        if error_col is not None:
            col_letter = _column_index_to_letter(error_col)
            # Ограничиваем длину сообщения об ошибке
            error_msg_short = error_msg[:500] if len(error_msg) > 500 else error_msg
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[error_msg_short]]
            })
        
        # Инкрементируем attempts
        if increment_attempts:
            attempts_col = _find_column_index(headers, "publish_attempts")
            if attempts_col is not None:
                current_attempts = 0
                try:
                    current_attempts = int(record.get(headers[attempts_col]) or 0)
                except (ValueError, TypeError):
                    pass
                
                col_letter = _column_index_to_letter(attempts_col)
                updates.append({
                    "range": f"{col_letter}{row_number}",
                    "values": [[str(current_attempts + 1)]]
                })
        
        # Обновляем last_try_at
        last_try_col = _find_column_index(headers, "publish_last_try_at")
        if last_try_col is not None:
            col_letter = _column_index_to_letter(last_try_col)
            updates.append({
                "range": f"{col_letter}{row_number}",
                "values": [[now_str]]
            })
        
        if updates:
            update_sheet_cells(spreadsheet_id, sheet_name, updates)
            logger.warning(f"[blog-publish] Ошибка записана для строки {row_number}: {error_msg[:100]}")
            
    except Exception as e:
        logger.error(f"[blog-publish] Ошибка при записи ошибки для строки {row_number}: {e}", exc_info=True)


def record_publish_error_by_id(sheet_id: str, error_code: str, logger=None) -> bool:
    """
    P0: Если row_number отсутствует/невалиден, пишем publish_error по уникальному совпадению ID.

    Важно: в этом режиме мы НЕ пишем canonical_url / published_posts и т.д. — только publish_error/attempts/last_try_at.
    """
    if logger is None:
        logger = get_logger(__name__)
    try:
        spreadsheet_id, sheet_name = resolve_parser_source()
        row_number, amb_code = _safe_find_row_number_by_unique_id(spreadsheet_id, sheet_name, sheet_id, logger=logger)
        if not row_number:
            logger.warning(f"[blog-publish] Невозможно безопасно определить строку для ошибки: id={sheet_id}, code={amb_code}")
            return False
        record_publish_error(row_number, error_code, increment_attempts=True, logger=logger)
        return True
    except Exception as e:
        logger.error(f"[blog-publish] Ошибка record_publish_error_by_id: {e}", exc_info=True)
        return False


def publish_ready_posts(db_session, logger=None) -> Dict[str, int]:
    """
    Обрабатывает записи со статусом READY_TO_PUBLISH.
    
    Алгоритм:
    1. Читает все записи из Sheets
    2. Фильтрует: status=READY_TO_PUBLISH AND published_posts!=TRUE
    3. Проверяет scheduled_at (если есть, должен быть <= now)
    4. Для каждой:
       - Пытается получить lock
       - Если lock получен:
         - Синхронизирует в БД (через существующую логику)
         - После успеха → ack_publish()
       - При ошибке → record_publish_error()
    
    Args:
        db_session: Сессия БД
        logger: Логгер (опционально)
    
    Returns:
        {"published": X, "failed": Y, "locked": Z, "skipped": W}
    """
    if logger is None:
        logger = get_logger(__name__)
    
    from app.services.blog.sync import sync_blog_from_parser_tab, _is_publishable, _safe_dt
    from app.database.models import BlogPost
    
    stats = {"published": 0, "failed": 0, "locked": 0, "skipped": 0}
    
    # Проверяем наличие publish-колонок перед публикацией
    try:
        from app.services.blog.sheets_columns import check_publish_columns
        all_exist, existing, missing = check_publish_columns()
        
        if not all_exist:
            logger.warning(
                f"[blog-publish] Отсутствуют publish-колонки: {missing}. "
                f"Публикация может работать некорректно. "
                f"Попытка автоматического создания колонок..."
            )
            # Пытаемся создать отсутствующие колонки
            from app.services.blog.sheets_columns import ensure_publish_columns_exist
            success, created = ensure_publish_columns_exist()
            if success and created:
                logger.info(f"[blog-publish] Автоматически созданы колонки: {', '.join(created)}")
            elif not success:
                logger.warning(
                    f"[blog-publish] Не удалось автоматически создать колонки. "
                    f"Публикация может работать некорректно."
                )
    except Exception as e:
        logger.warning(f"[blog-publish] Ошибка при проверке колонок (не критично): {e}")
        # Продолжаем работу, даже если проверка колонок не удалась
    
    # Добавляем детальные счётчики для диагностики
    debug_stats = {
        "total_records": 0,
        "no_id": 0,
        "not_ready_status": 0,
        "ready_to_publish_count": 0,
        "already_published": 0,
        "scheduled_future": 0,
        "not_publishable": 0,
        "no_row_number": 0
    }
    
    try:
        # Читаем все записи из Sheets
        records, headers = fetch_parser_news_rows()
        debug_stats["total_records"] = len(records)
        logger.info(f"[blog-publish] Проверка {len(records)} записей на готовность к публикации")
        
        # P0: валидация схемы ДО любых writeback
        schema_ok, missing_cols = _validate_writeback_schema(headers)
        if not schema_ok:
            logger.warning(f"[blog-publish] Несовпадение схемы Sheets (publish_ready_posts): missing={missing_cols}")
        
        now = datetime.utcnow()
        
        # Собираем статистику по всем статусам для диагностики
        status_counts = {}
        
        for index, row in enumerate(records):
            sheet_id = str(row.get("id") or row.get("news_id") or row.get("raw_id") or "").strip()
            if not sheet_id:
                debug_stats["no_id"] += 1
                continue
            
            # Фильтруем: status=READY_TO_PUBLISH
            status = str(row.get("status") or "").strip().upper()
            
            # Собираем статистику по статусам
            status_key = status if status else "(пусто)"
            status_counts[status_key] = status_counts.get(status_key, 0) + 1
            
            if status != "READY_TO_PUBLISH":
                if status:  # Логируем только если статус не пустой
                    debug_stats["not_ready_status"] += 1
                continue
            
            # Нашли запись со статусом READY_TO_PUBLISH
            debug_stats["ready_to_publish_count"] += 1
            logger.debug(f"[blog-publish] Найдена запись READY_TO_PUBLISH: id={sheet_id}, row={index+2}")
            
            # Проверяем published_posts
            published_posts = str(row.get("published_posts") or "").strip().upper()
            if published_posts in ("TRUE", "1", "YES", "ДА"):
                debug_stats["already_published"] += 1
                stats["skipped"] += 1
                logger.debug(f"[blog-publish] Запись {sheet_id} уже опубликована (published_posts=TRUE)")
                continue
            
            # Проверяем scheduled_at
            scheduled_at_raw = _safe_dt(row.get("scheduled_at"))
            # Нормализуем к naive UTC для безопасного сравнения
            from app.services.blog.sync import _normalize_to_naive_utc
            scheduled_at = _normalize_to_naive_utc(scheduled_at_raw)
            if scheduled_at and scheduled_at > now:
                debug_stats["scheduled_future"] += 1
                stats["skipped"] += 1
                logger.debug(f"[blog-publish] Запись {sheet_id} запланирована на будущее: {scheduled_at}")
                continue
            
            # Проверяем публикуемость (должна быть True для READY_TO_PUBLISH)
            if not _is_publishable(row):
                debug_stats["not_publishable"] += 1
                stats["skipped"] += 1
                # Детальная диагностика почему не публикуется
                final_posts = str(row.get("final_posts") or "").strip()
                text = str(row.get("text") or "").strip()
                final_ready = str(row.get("final_ready") or "").strip().upper()
                logger.warning(
                    f"[blog-publish] Запись {sheet_id} не прошла проверку публикуемости: "
                    f"final_posts={'есть' if final_posts else 'нет'}, "
                    f"text={'есть' if text else 'нет'}, "
                    f"final_ready={final_ready}"
                )
                continue
            
            # Получаем row_number
            row_number = _get_row_number_from_record(row, index)
            if not row_number:
                debug_stats["no_row_number"] += 1
                stats["failed"] += 1
                ok, n, code = _validate_row_number(row.get("row_number"))
                code = code or WP_ROW_NUMBER_INVALID
                logger.warning(f"[blog-publish] row_number отсутствует/невалиден для id={sheet_id}: {code}")
                # P0: пробуем записать publish_error по уникальному совпадению ID
                record_publish_error_by_id(sheet_id, code, logger=logger)
                continue

            # Если схема невалидна — не публикуем, но фиксируем WP_SCHEMA_MISMATCH
            if not schema_ok:
                stats["failed"] += 1
                record_publish_error(row_number, WP_SCHEMA_MISMATCH, increment_attempts=False, logger=logger)
                continue
            
            # Пытаемся получить lock
            if not acquire_publish_lock(row_number, logger=logger):
                stats["locked"] += 1
                logger.debug(f"[blog-publish] Не удалось получить lock для записи {sheet_id} (строка {row_number})")
                continue
            
            try:
                # Синхронизируем в БД (используем существующую логику)
                # Но только для этой конкретной записи
                post = db_session.get(BlogPost, sheet_id)
                
                # Если пост уже есть и checksum совпадает - просто подтверждаем публикацию
                from app.services.blog.sync import _stable_checksum
                checksum = _stable_checksum(row)
                
                if post and post.checksum == checksum and post.status in ("PUBLISHED", "published"):
                    # Уже синхронизирован и опубликован - просто подтверждаем
                    logger.debug(f"[blog-publish] Пост {sheet_id} уже опубликован в БД")
                else:
                    # Синхронизируем (создаём или обновляем)
                    # Используем упрощённую версию логики из sync_blog_from_parser_tab
                    from app.services.blog.render import safe_render_markdown
                    from app.services.blog.sync import _parse_tags, _slugify
                    
                    title = str(row.get("title") or row.get("raw_title") or "").strip()
                    if not title:
                        title = f"Материал {sheet_id}"
                    
                    final_posts = str(row.get("final_posts") or row.get("text") or "").strip()
                    content_md = final_posts
                    content_html = safe_render_markdown(content_md)
                    
                    # excerpt: сначала из summary/lead, если нет - генерируем из контента
                    summary = str(row.get("summary") or row.get("lead") or "").strip()
                    if summary:
                        excerpt = summary[:280]
                    elif final_posts:
                        # Генерируем excerpt из первых 3-4 строк основного текста
                        text = re.sub(r'<[^>]+>', '', content_html)  # Убираем HTML
                        text = re.sub(r'[#*\[\]()]', '', text)  # Убираем markdown символы
                        text = text.strip()
                        # Берем первые 200-250 символов (примерно 3-4 строки)
                        if len(text) > 250:
                            # Обрезаем по последнему пробелу перед 250 символом
                            excerpt = text[:250].rsplit(' ', 1)[0] + '...'
                        else:
                            excerpt = text
                    else:
                        excerpt = None
                    
                    tags = _parse_tags(row.get("raw_tags") or row.get("tags"), row.get("ne"))
                    
                    published_at = _safe_dt(row.get("published_at")) or _safe_dt(row.get("updated_at")) or _safe_dt(row.get("created_at")) or datetime.utcnow()
                    
                    if not post:
                        post = BlogPost(
                            id=sheet_id,
                            title=title,
                            slug=_slugify(title, sheet_id),
                        )
                    else:
                        # Обновляем существующий
                        pass
                    
                    post.source_type = str(row.get("source_type") or "").strip() or None
                    post.source_name = str(row.get("source_name") or "").strip() or None
                    post.source_url = str(row.get("source_url") or "").strip() or None
                    post.title = title
                    
                    sheet_slug = str(row.get("slug") or "").strip()
                    if sheet_slug:
                        post.slug = sheet_slug
                    elif not post.slug:
                        post.slug = _slugify(title, sheet_id)
                    
                    post.excerpt = excerpt
                    post.content_md = content_md
                    post.content_html = content_html
                    post.content = content_html
                    post.teaser = excerpt or ""  # teaser не может быть None из-за ограничения БД
                    
                    cover = str(row.get("cover_image_url") or row.get("image_url") or "").strip()
                    if not cover:
                        raw_media = row.get("raw_media")
                        if raw_media:
                            s = str(raw_media).strip()
                            if s.startswith("[") and s.endswith("]"):
                                try:
                                    arr = json.loads(s)
                                    if isinstance(arr, list) and arr:
                                        cover = str(arr[0])
                                except Exception:
                                    pass
                            elif s.startswith("http"):
                                cover = s
                    post.cover_image_url = cover or None
                    
                    # Встраиваем медиа из media_json в контент (если есть)
                    # Исключаем cover image, чтобы не дублировать
                    from app.services.blog.store import _embed_media_from_json
                    media_html = _embed_media_from_json(row.get("media_json"), exclude_url=cover)
                    if media_html:
                        # Добавляем медиа после основного контента
                        post.content_html = post.content_html + "\n" + media_html
                        post.content = post.content_html
                    
                    post.tags_json = json.dumps(tags, ensure_ascii=False) if tags else None
                    post.lang = str(row.get("lang") or "").strip() or None
                    post.checksum = checksum
                    post.status = "PUBLISHED"
                    post.published_at = published_at
                    
                    try:
                        post.sheet_row_number = int(row.get("row_number") or 0) or None
                    except Exception:
                        post.sheet_row_number = None
                    
                    db_session.add(post)
                    db_session.commit()
                    logger.info(f"[blog-publish] Пост {sheet_id} синхронизирован в БД")
                
                # Подтверждаем публикацию (ack)
                slug = post.slug if post else None
                if ack_publish(row_number, sheet_id, published_at, slug=slug, logger=logger):
                    stats["published"] += 1
                    logger.info(f"[blog-publish] Пост {sheet_id} опубликован (строка {row_number})")
                else:
                    # Если ack не удался, но БД обновлена - всё равно считаем успехом
                    # но записываем предупреждение
                    stats["published"] += 1
                    logger.warning(f"[blog-publish] Пост {sheet_id} опубликован в БД, но ack в Sheets не отправлен")
                
            except Exception as e:
                # Ошибка при синхронизации или ack
                # Rollback для очистки состояния сессии
                try:
                    db_session.rollback()
                except Exception:
                    pass
                error_msg = str(e)
                record_publish_error(row_number, error_msg, increment_attempts=True, logger=logger)
                release_publish_lock(row_number, logger=logger)
                stats["failed"] += 1
                logger.error(f"[blog-publish] Ошибка публикации поста {sheet_id}: {e}", exc_info=True)
        
        logger.info(
            f"[blog-publish] Статистика: опубликовано={stats['published']}, "
            f"ошибок={stats['failed']}, заблокировано={stats['locked']}, пропущено={stats['skipped']}"
        )
        
        # Детальная диагностика - ВСЕГДА выводим
        logger.info(
            f"[blog-publish] Детальная диагностика: "
            f"всего записей={debug_stats['total_records']}, "
            f"без ID={debug_stats['no_id']}, "
            f"с другими статусами={debug_stats['not_ready_status']}, "
            f"найдено READY_TO_PUBLISH={debug_stats['ready_to_publish_count']}"
        )
        
        # Выводим статистику по всем статусам
        if status_counts:
            status_list = ", ".join([f"{k}: {v}" for k, v in sorted(status_counts.items(), key=lambda x: -x[1])[:10]])
            logger.info(f"[blog-publish] Распределение статусов (топ-10): {status_list}")
        
        if debug_stats["ready_to_publish_count"] == 0:
            logger.warning(
                f"[blog-publish] ВНИМАНИЕ: Не найдено записей со статусом READY_TO_PUBLISH! "
                f"Всего записей: {debug_stats['total_records']}, "
                f"без ID: {debug_stats['no_id']}, "
                f"с другими статусами: {debug_stats['not_ready_status']}"
            )
        else:
            logger.info(
                f"[blog-publish] Детальная статистика по READY_TO_PUBLISH: "
                f"найдено={debug_stats['ready_to_publish_count']}, "
                f"уже опубликовано={debug_stats['already_published']}, "
                f"запланировано на будущее={debug_stats['scheduled_future']}, "
                f"не прошли проверку публикуемости={debug_stats['not_publishable']}, "
                f"нет row_number={debug_stats['no_row_number']}"
            )
        
        return stats
        
    except Exception as e:
        logger.error(f"[blog-publish] Критическая ошибка при публикации готовых постов: {e}", exc_info=True)
        return stats

