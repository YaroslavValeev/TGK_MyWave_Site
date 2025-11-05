from flask import Flask
import logging
from app.services.google import get_google_services
import os
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Настройка конфигурации
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / 'configs'

def find_service_account_file():
    possible_paths = [
        str(CONFIG_DIR / 'service_account.json'),
        str(BASE_DIR / 'instance' / 'service_account.json'),
        str(BASE_DIR / 'service_account.json')
    ]
    
    env_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    if env_path and os.path.isfile(env_path):
        return env_path
        
    for path in possible_paths:
        if os.path.isfile(path):
            return path
            
    return str(CONFIG_DIR / 'service_account.json')

def create_minimal_app():
    app = Flask(__name__)
    app.config['GOOGLE_SERVICE_ACCOUNT_FILE'] = find_service_account_file()
    app.config['SPREADSHEET_ID'] = os.getenv('SPREADSHEET_ID', '1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0')
    return app

if __name__ == "__main__":
    app = create_minimal_app()
    
    with app.app_context():
        print("\nПроверка конфигурации:")
        print("-" * 50)
        print(f"SPREADSHEET_ID = {app.config.get('SPREADSHEET_ID')}")
        print(f"GOOGLE_SERVICE_ACCOUNT_FILE = {app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')}")
        
        print("\nПроверка файла сервисного аккаунта:")
        print("-" * 50)
        service_account_path = app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')
        if os.path.exists(service_account_path):
            print(f"✅ Файл найден: {service_account_path}")
        else:
            print(f"❌ Файл не найден: {service_account_path}")
        
        print("\nПроверка Google API:")
        print("-" * 50)
        try:
            drive, sheets, calendar = get_google_services()  # Получаем все три сервиса
            print("✅ Google сервисы инициализированы успешно")
            
            # Пробуем получить доступ к таблице
            result = sheets.spreadsheets().values().get(
                spreadsheetId=app.config['SPREADSHEET_ID'],
                range="Schedule!A1:A1"
            ).execute()
            print("✅ Доступ к таблице получен успешно")
            print(f"✅ Данные получены: {result}")
            
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            logger.exception("Подробности ошибки:")