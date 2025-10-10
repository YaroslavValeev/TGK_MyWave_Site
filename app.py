from flask import Blueprint, request, jsonify
from websocket_handler import ws_handler, connected_clients
import os
import logging
from app import create_app

# Оставляем только логику API и необходимые импорты для Blueprint

api_bp = Blueprint('api', __name__)

# API для чата
@api_bp.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    # Имитация ответа эксперта
    return jsonify(reply=f"Вы сказали: {message}")

# API для загрузки файлов
@api_bp.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        return jsonify(error="Нет файла в запросе"), 400
    file = request.files["file"]
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)
    return jsonify(file_id=file.filename)

# API для бронирования
@api_bp.route("/book", methods=["POST"])
def book():
    booking_data = request.get_json()
    # Простейшая имитация бронирования
    return jsonify(success=True)

@api_bp.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

# Добавляем заголовок Content Security Policy

if __name__ == '__main__':
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
