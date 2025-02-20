from flask import Blueprint, jsonify, request, current_app
import datetime

bp = Blueprint("booking", __name__)

@bp.route("/book", methods=["POST"])
def book_training():
    try:
        data = request.get_json()

        # Проверка, что все нужные поля переданы
        required_fields = ["date", "slot", "name", "phone"]
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Все поля обязательны"}), 400

        # Проверка форматов даты и времени
        try:
            datetime.datetime.strptime(data["date"], "%Y-%m-%d")
            datetime.datetime.strptime(data["slot"], "%H:%M")
        except ValueError:
            return jsonify({"error": "Неверный формат даты/времени"}), 400

        # Эмуляция успешного бронирования
        return jsonify({"status": "success", "message": "Тренировка успешно забронирована!"}), 200

    except Exception as e:
        current_app.logger.error(f"Ошибка бронирования: {str(e)}")
        return jsonify({"error": "Ошибка обработки запроса"}), 500
