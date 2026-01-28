"""
Сервис для обработки регистраций WakeSurf Challenge 2025.
"""
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
from flask import current_app
from app.services.google_sheets_service import append_record, read_records
from app.services.projects.validation import normalize_phone, sanitize_text


def save_participant_registration(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Сохранение регистрации участника.
    
    Args:
        data: Данные формы регистрации участника
    
    Returns:
        (success, error_message)
    """
    try:
        spreadsheet_id = current_app.config.get('WSC2025_SPREADSHEET_ID')
        sheet_name = current_app.config.get('WSC2025_PARTICIPANTS_SHEET', 'WSC2025_Participants')
        
        if not spreadsheet_id:
            return False, "Не настроен SPREADSHEET_ID для проекта"
        
        # Подготовка данных для сохранения
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Дата регистрации
            sanitize_text(data.get('full_name', ''), 100),  # ФИО
            normalize_phone(data.get('phone', '')),  # Телефон (нормализованный)
            data.get('email', '').lower().strip(),  # Email
            data.get('birth_year', ''),  # Год рождения
            data.get('level', ''),  # Уровень
            sanitize_text(data.get('city', 'Москва'), 50),  # Город
            sanitize_text(data.get('goals', ''), 500),  # Цели участия
            'Да' if data.get('consent_participation') else 'Нет',  # Согласие на участие
            'Да' if data.get('consent_media') else 'Нет',  # Согласие на медиа
        ]
        
        # Сохранение в Google Sheets
        append_record(spreadsheet_id, sheet_name, row)
        
        current_app.logger.info(f"Участник зарегистрирован: {data.get('full_name')} ({data.get('email')})")
        
        return True, None
        
    except Exception as e:
        current_app.logger.error(f"Ошибка сохранения регистрации участника: {e}", exc_info=True)
        return False, f"Ошибка при сохранении данных: {str(e)}"


def save_coach_registration(data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Сохранение регистрации тренера.
    
    Args:
        data: Данные формы регистрации тренера
    
    Returns:
        (success, error_message)
    """
    try:
        spreadsheet_id = current_app.config.get('WSC2025_SPREADSHEET_ID')
        sheet_name = current_app.config.get('WSC2025_COACHES_SHEET', 'WSC2025_Coaches')
        
        if not spreadsheet_id:
            return False, "Не настроен SPREADSHEET_ID для проекта"
        
        # Подготовка данных для сохранения
        row = [
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),  # Дата регистрации
            sanitize_text(data.get('full_name', ''), 100),  # ФИО
            normalize_phone(data.get('phone', '')),  # Телефон (нормализованный)
            data.get('email', '').lower().strip(),  # Email
            sanitize_text(data.get('club', ''), 100),  # Клуб/школа
            data.get('experience_years', ''),  # Опыт (лет)
            sanitize_text(data.get('portfolio_url', ''), 500),  # Портфолио
            'Да' if data.get('consent_participation') else 'Нет',  # Согласие на участие
            'Да' if data.get('consent_media') else 'Нет',  # Согласие на медиа
        ]
        
        # Сохранение в Google Sheets
        append_record(spreadsheet_id, sheet_name, row)
        
        current_app.logger.info(f"Тренер зарегистрирован: {data.get('full_name')} ({data.get('email')})")
        
        return True, None
        
    except Exception as e:
        current_app.logger.error(f"Ошибка сохранения регистрации тренера: {e}", exc_info=True)
        return False, f"Ошибка при сохранении данных: {str(e)}"

