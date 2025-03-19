from flask import Flask, request, jsonify, send_from_directory
import os

app = Flask(__name__, static_folder="static", template_folder="templates")

# Маршрут для главной страницы
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")  # index.html должен ссылаться на chat.js и style.css

# API для чата
@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json()
    message = data.get("message", "")
    # Имитация ответа эксперта
    return jsonify(reply=f"Вы сказали: {message}")

# API для загрузки файлов
@app.route("/upload", methods=["POST"])
def upload():
    if 'file' not in request.files:
        return jsonify(error="Нет файла в запросе"), 400
    file = request.files["file"]
    os.makedirs("uploads", exist_ok=True)
    file_path = os.path.join("uploads", file.filename)
    file.save(file_path)
    return jsonify(file_id=file.filename)

# API для бронирования
@app.route("/book", methods=["POST"])
def book():
    booking_data = request.get_json()
    # Простейшая имитация бронирования
    return jsonify(success=True)

if __name__ == "__main__":
    app.run(debug=True)
