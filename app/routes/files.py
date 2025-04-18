from flask import Blueprint, request, jsonify, current_app
from app.services.google import GoogleService
from googleapiclient.http import MediaFileUpload

bp = Blueprint('files', __name__, url_prefix='/files')

ALLOWED_EXTENSIONS = {"jpg", "jpeg", "png", "pdf", "mp4", "mov", "xlsx", "zip"}

def upload_to_drive_from_stream(file, folder_id):
    """Загружает файл на Google Drive."""
    try:
        drive_service = current_app.drive_service
        file_metadata = {
            "name": file.filename,
            "parents": [folder_id]
        }
        media = MediaFileUpload(file.stream, mimetype=file.content_type)
        uploaded_file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()
        return uploaded_file.get("id")
    except Exception as e:
        raise Exception(f"Ошибка загрузки файла: {str(e)}")

def list_user_files(user_id):
    """Возвращает список файлов пользователя."""
    try:
        drive_service = current_app.drive_service
        query = f"name contains '{user_id}'"
        results = drive_service.files().list(q=query, fields="files(id, name)").execute()
        return results.get("files", [])
    except Exception as e:
        raise Exception(f"Ошибка получения файлов: {str(e)}")

@bp.route('/upload', methods=['POST'])
def upload_file():
    """Обработка загрузки файлов."""
    file = request.files.get('file')
    user_id = request.form.get('user_id')

    if not file or not user_id:
        return jsonify({"error": "Файл или ID пользователя не предоставлены"}), 400

    # 🔒 Проверка допустимых расширений
    if not file.filename.lower().endswith(tuple(ALLOWED_EXTENSIONS)):
        return jsonify({"success": False, "error": "Недопустимый формат файла"}), 400

    try:
        folder_id = current_app.config.get("DRIVE_FOLDER_ID")
        drive_file_id = upload_to_drive_from_stream(file, folder_id)

        current_app.logger.info(f"✅ Файл {file.filename} загружен в Google Drive пользователем {user_id}")

        google_service = GoogleService()
        download_link = google_service.create_drive_link(drive_file_id)
        return jsonify({
            "status": "success",
            "file_id": drive_file_id,
            "download_link": download_link
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/list', methods=['GET'])
def list_files():
    """Возвращает список файлов пользователя."""
    user_id = request.args.get('user_id')
    
    if not user_id:
        return jsonify({"error": "ID пользователя не предоставлен"}), 400

    try:
        files = list_user_files(user_id)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
