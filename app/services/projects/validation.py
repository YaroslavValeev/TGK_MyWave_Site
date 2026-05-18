"""
Утилиты для валидации и санитизации данных для проектов.
"""
import re
import bleach
from typing import Optional, Tuple
from flask import current_app


def sanitize_text(text: str, max_length: Optional[int] = None) -> str:
    """
    Санитизация текстового поля от XSS.
    
    Args:
        text: Входной текст
        max_length: Максимальная длина (если указана)
    
    Returns:
        Очищенный текст
    """
    if not text:
        return ""
    
    # Удаляем HTML теги, оставляем только безопасный текст
    cleaned = bleach.clean(text, tags=[], strip=True)
    
    if max_length and len(cleaned) > max_length:
        cleaned = cleaned[:max_length]
    
    return cleaned.strip()


def validate_phone(phone: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация российского телефонного номера.
    
    Args:
        phone: Номер телефона
    
    Returns:
        (is_valid, error_message)
    """
    if not phone:
        return False, "Телефон обязателен для заполнения"
    
    # Удаляем все нецифровые символы кроме +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем форматы: +7XXXXXXXXXX или 8XXXXXXXXXX
    if re.match(r'^\+7\d{10}$', cleaned):
        return True, None
    elif re.match(r'^8\d{10}$', cleaned):
        return True, None
    elif re.match(r'^7\d{10}$', cleaned):
        # Нормализуем к +7
        return True, None
    else:
        return False, "Неверный формат телефона. Используйте +7XXXXXXXXXX или 8XXXXXXXXXX"


def normalize_phone(phone: str) -> str:
    """
    Нормализация телефонного номера к формату +7XXXXXXXXXX.
    
    Args:
        phone: Номер телефона
    
    Returns:
        Нормализованный номер
    """
    if not phone:
        return ""
    
    # Удаляем все нецифровые символы кроме +
    cleaned = re.sub(r'[^\d+]', '', phone)
    
    # Нормализуем к +7XXXXXXXXXX
    if cleaned.startswith('+7'):
        return cleaned
    elif cleaned.startswith('8'):
        return '+7' + cleaned[1:]
    elif cleaned.startswith('7'):
        return '+' + cleaned
    else:
        return '+7' + cleaned


def validate_email(email: str) -> Tuple[bool, Optional[str]]:
    """
    Валидация email адреса.
    
    Args:
        email: Email адрес
    
    Returns:
        (is_valid, error_message)
    """
    if not email:
        return False, "Email обязателен для заполнения"
    
    # Простая проверка формата
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if re.match(pattern, email):
        return True, None
    else:
        return False, "Неверный формат email адреса"


def validate_birth_year(year: int) -> Tuple[bool, Optional[str]]:
    """
    Валидация года рождения.
    
    Args:
        year: Год рождения
    
    Returns:
        (is_valid, error_message)
    """
    from datetime import datetime
    current_year = datetime.now().year
    
    if year < 1930:
        return False, "Год рождения не может быть раньше 1930"
    elif year > current_year - 5:  # Минимум 5 лет
        return False, f"Год рождения не может быть позже {current_year - 5}"
    else:
        return True, None


def check_duplicate_email(email: str, sheet_name: str) -> bool:
    """
    Проверка дубликата email в Google Sheets.
    
    Args:
        email: Email для проверки
        sheet_name: Название листа
    
    Returns:
        True если дубликат найден
    """
    try:
        from app.services.google_sheets_service import read_records
        spreadsheet_id = (
            current_app.config.get('WSC2025_SPREADSHEET_ID')
            or current_app.config.get('SPREADSHEET_ID')
        )
        if not spreadsheet_id:
            return False
        
        records = read_records(spreadsheet_id, sheet_name)
        if not records:
            return False
        
        target = email.lower().strip()
        for record in records:
            if not isinstance(record, dict):
                continue
            record_email = str(
                record.get('email') or record.get('Email') or ''
            ).strip().lower()
            if record_email and record_email == target:
                return True
        
        return False
    except Exception as e:
        current_app.logger.error(f"Ошибка проверки дубликата email: {e}")
        return False


def check_duplicate_phone(phone: str, sheet_name: str) -> bool:
    """
    Проверка дубликата телефона в Google Sheets.
    
    Args:
        phone: Телефон для проверки
        sheet_name: Название листа
    
    Returns:
        True если дубликат найден
    """
    try:
        from app.services.google_sheets_service import read_records
        spreadsheet_id = (
            current_app.config.get('WSC2025_SPREADSHEET_ID')
            or current_app.config.get('SPREADSHEET_ID')
        )
        if not spreadsheet_id:
            return False
        
        records = read_records(spreadsheet_id, sheet_name)
        if not records:
            return False
        
        normalized_phone = normalize_phone(phone)
        
        for record in records:
            if not isinstance(record, dict):
                continue
            record_phone = str(
                record.get('phone') or record.get('Телефон') or record.get('Phone') or ''
            ).strip()
            if record_phone and normalize_phone(record_phone) == normalized_phone:
                return True
        
        return False
    except Exception as e:
        current_app.logger.warning(f"Ошибка проверки дубликата телефона (пропускаем проверку): {e}")
        # При ошибке не блокируем регистрацию
        return False

