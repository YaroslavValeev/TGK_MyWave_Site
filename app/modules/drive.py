from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from app.services.google import drive_service
from datetime import datetime

def upload_to_drive_from_path(file_path, folder_id=None):
    """
    Загружает файл на Google Диск по указанному локальному пути.
    
    Аргументы:
        file_path (str): Путь к файлу на локальном диске
        folder_id (str, optional): ID папки на Google Drive, куда загружать файл
    
    Возвращает:
        str: ID загруженного файла на Google Drive
    
    Исключения:
        HttpError: При ошибке загрузки файла
    """
    try:
        file_metadata = {"name": file_path.split("/")[-1]}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        media = MediaFileUpload(file_path, resumable=True)
        file = drive_service.files().create(
            body=file_metadata, media_body=media, fields="id"
        ).execute()
        return file.get("id")
    except HttpError as error:
        print(f"Произошла ошибка: {error}")
        raise

def upload_to_drive_from_stream(file, folder_id=None):
    """
    Загружает файл, полученный через форму, на Google Диск.
    
    Аргументы:
        file (FileStorage): Объект файла из Flask-формы
        folder_id (str, optional): ID папки на Google Drive, куда загружать файл
    
    Возвращает:
        str: ID загруженного файла на Google Drive
    
    Исключения:
        ValueError: Если файл не является изображением
        HttpError: При ошибке загрузки файла
    """
    if not file.content_type.startswith('image/'):
        raise ValueError("Только изображения разрешены")

    file_metadata = {"name": file.filename}
    if folder_id:
        file_metadata["parents"] = [folder_id]

    media = MediaFileUpload(file.stream, mimetype=file.content_type)
    file_response = drive_service.files().create(
        body=file_metadata, media_body=media, fields="id"
    ).execute()
    return file_response.get("id")

def list_user_files(user_id):
    """
    Получает список файлов из подтвержденных записей в таблице Client_Workouts.
    
    Аргументы:
        user_id (str): ID пользователя, для которого ищутся файлы
    
    Возвращает:
        list: Список словарей с информацией о файлах (id и name)
    
    Исключения:
        HttpError: При ошибке получения данных из таблицы
    """
    try:
        # Query Client_Workouts table for confirmed bookings
        sheets_service = get_google_services()[1]
        spreadsheet_id = current_app.config["SPREADSHEET_ID"]
        range_name = "Client_Workouts!A2:E"
        
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        files = []
        for row in result.get('values', []):
            if len(row) >= 5 and row[2] == user_id:  # Check user_id in Client_Workouts
                # Предполагаем, что в row[1] хранится дата и время в формате "YYYY-MM-DD HH:MM"
                try:
                    dt = datetime.strptime(row[1], "%Y-%m-%d %H:%M")
                    date_str = dt.strftime("%Y-%m-%d")
                    time_str = dt.strftime("%H:%M")
                    formatted_datetime = f"{date_str} {time_str}"
                except ValueError:
                    formatted_datetime = row[1]  # Оставляем как есть, если формат неверный
                
                files.append({
                    "id": row[0],
                    "name": f"{user_id}_{formatted_datetime}"
                })
        return files
    except HttpError as error:
        print(f"Произошла ошибка: {error}")
        raise