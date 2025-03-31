import gspread
from google.oauth2.service_account import Credentials
import logging
import os
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Настрой логирование
logger = logging.getLogger(__name__)

GOOGLE_SHEETS_FILE_NAME = "MyWave_Admin_Tg_Bot - Clients (1)"  # Имя файла в Google Drive
GOOGLE_SHEET_NAME = "clients"  # Имя листа, как на скриншоте
CREDENTIALS_FILE = "credentials.json"  # Путь к файлу авторизации

def authorize_gspread(credentials_file):
    """
    Авторизация в Google Sheets.
    
    Args:
        credentials_file (str): Путь к файлу учетных данных
        
    Returns:
        gspread.Client: Авторизованный клиент
        
    Raises:
        FileNotFoundError: Если файл учетных данных не найден
        ValueError: Если файл учетных данных некорректный
    """
    try:
        if not os.path.exists(credentials_file):
            raise FileNotFoundError(f"Файл учетных данных не найден: {credentials_file}")
            
        scopes = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_file(credentials_file, scopes=scopes)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        logger.error(f"Ошибка авторизации в Google Sheets: {str(e)}")
        raise

def get_sheet_data(credentials_file, sheet_id, worksheet_name):
    """
    Получение данных из таблицы.
    
    Args:
        credentials_file (str): Путь к файлу учетных данных
        sheet_id (str): ID таблицы
        worksheet_name (str): Название листа
        
    Returns:
        list: Список записей из таблицы
        
    Raises:
        ValueError: Если параметры некорректны
        Exception: При ошибках доступа к таблице
    """
    try:
        if not all([credentials_file, sheet_id, worksheet_name]):
            raise ValueError("Не все необходимые параметры предоставлены")
            
        client = authorize_gspread(credentials_file)
        sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
        records = sheet.get_all_records()
        
        if not records:
            logger.warning(f"Таблица {worksheet_name} пуста")
            return []
            
        return records
    except Exception as e:
        logger.error(f"Ошибка получения данных из таблицы: {str(e)}")
        return []

def append_to_sheet(credentials_file, sheet_id, worksheet_name, row_data):
    """
    Запись данных в таблицу.
    
    Args:
        credentials_file (str): Путь к файлу учетных данных
        sheet_id (str): ID таблицы
        worksheet_name (str): Название листа
        row_data (list): Данные для записи
        
    Raises:
        ValueError: Если параметры некорректны
        Exception: При ошибках записи в таблицу
    """
    try:
        if not all([credentials_file, sheet_id, worksheet_name, row_data]):
            raise ValueError("Не все необходимые параметры предоставлены")
            
        if not isinstance(row_data, list):
            raise ValueError("Данные должны быть в виде списка")
            
        client = authorize_gspread(credentials_file)
        sheet = client.open_by_key(sheet_id).worksheet(worksheet_name)
        sheet.append_row(row_data)
        logger.info(f"Данные успешно добавлены в таблицу {worksheet_name}")
    except Exception as e:
        logger.error(f"Ошибка записи данных в таблицу: {str(e)}")
        raise

def get_history_by_client_id(client_id):
    """Получение всей истории сообщений по client_id"""
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(credentials)
    sheet = client.open(GOOGLE_SHEETS_FILE_NAME).worksheet(GOOGLE_SHEET_NAME)
    records = sheet.get_all_records()
    return [
        {"role": "user", "content": row["message"]}
        for row in records if row.get("client_id") == client_id
    ]

def save_message(client_id, message):
    """Сохраняет новое сообщение в таблицу"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(credentials)
    sheet = client.open(GOOGLE_SHEETS_FILE_NAME).worksheet(GOOGLE_SHEET_NAME)
    sheet.append_row([client_id, now, message])
