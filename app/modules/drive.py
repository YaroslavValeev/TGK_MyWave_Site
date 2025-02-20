from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from app.services.google import drive_service  # drive_service должен быть настроен заранее

def upload_to_drive_from_path(file_path, folder_id=None):
    """
    Загружает файл на Google Диск по указанному локальному пути.
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
    Требует, чтобы MIME-тип файла начинался с "image/".
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
    Примерная функция для получения списка файлов пользователя.
    Реализуйте логику поиска файлов по user_id (например, фильтрация по имени файла).
    Возвращает список файлов.
    """
    try:
        # Здесь необходимо реализовать поиск файлов, например, с использованием запроса к Google Drive API
        # Данный пример возвращает статичные данные
        files = [
            {"id": "1", "name": f"{user_id}_example1.jpg"},
            {"id": "2", "name": f"{user_id}_example2.png"}
        ]
        return files
    except HttpError as error:
        print(f"Произошла ошибка: {error}")
        raise