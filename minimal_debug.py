from flask import Flask
import logging
from app.services.google import get_google_services
from app.config import Config

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def create_minimal_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    return app

if __name__ == "__main__":
    app = create_minimal_app()
    
    with app.app_context():
        print("\nПроверка конфигурации:")
        print("-" * 50)
        print(f"SPREADSHEET_ID = {app.config.get('SPREADSHEET_ID')}")
        print(f"GOOGLE_SERVICE_ACCOUNT_FILE = {app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')}")
        
        print("\nПроверка сервисного аккаунта:")
        print("-" * 50)
        try:
            calendar, sheets = get_google_services()
            print("✅ Google сервисы инициализированы успешно")
            
            # Пробуем получить доступ к таблице
            result = sheets.spreadsheets().values().get(
                spreadsheetId=app.config['SPREADSHEET_ID'],
                range="Schedule!A1:A1"
            ).execute()
            print("✅ Доступ к таблице получен успешно")
            
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            logger.exception("Подробности ошибки:")