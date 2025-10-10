import os
from pathlib import Path

# Базовые настройки
BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / 'configs'

# Настройки Google Sheets
# Try to find service account file in various locations
def find_service_account_file():
    possible_paths = [
        str(CONFIG_DIR / 'service_account.json'),  # In configs directory
        str(Path(__file__).resolve().parent.parent / 'instance' / 'service_account.json'),  # In instance directory
        str(Path(__file__).resolve().parent.parent / 'service_account.json')  # In root directory
    ]
    
    # First check environment variable
    env_path = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    if env_path and os.path.isfile(env_path):
        return env_path
        
    # Then try all possible paths
    for path in possible_paths:
        if os.path.isfile(path):
            return path
            
    # If not found, return the default path (will be checked later)
    return str(CONFIG_DIR / 'service_account.json')

GOOGLE_SERVICE_ACCOUNT_FILE = find_service_account_file()
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')  # ID таблицы из URL
GOOGLE_SHEETS_FILE_NAME = os.getenv('GOOGLE_SHEETS_FILE_NAME', 'MyWave_Admin_Tg_Bot - Clients (1)')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME', 'clients')

# Настройки OpenAI
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
GPTS_MODEL = os.getenv('GPTS_MODEL', 'gpt-4')
FINE_TUNED_MODEL = os.getenv('FINE_TUNED_MODEL', 'gpt-4')
FALLBACK_MODEL = os.getenv('FALLBACK_MODEL', 'gpt-4')

# Настройки Telegram
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')  # Полный URL вашего сайта

# Настройки логирования
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Настройки приложения
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY')  # Без fallback значения для безопасности 