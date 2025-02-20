import os
import logging
from flask import Flask, render_template, request, jsonify, current_app
from flask_login import LoginManager
from flask_sqlalchemy.extension import SQLAlchemy
from flask_talisman import Talisman
from flask_wtf.csrf import CSRFProtect
from flask_admin import Admin
from prometheus_flask_exporter import PrometheusMetrics
from flask_socketio import SocketIO
from config import Config, DevelopmentConfig

# Локальные импорты
from app.database import db
from app.routes.auth import bp as auth_bp
from app.routes.chat import bp as chat_bp
from app.routes.files import bp as files_bp
from app.routes.calendar import calendar_bp
from app.services.google import init_google_services
from app.utils import notify_admin
from app.database.models import User, Analytics
from app.routes.book import bp as book_bp

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
csrf = CSRFProtect(app)
app.config.from_object(Config)
app.config.from_object(DevelopmentConfig)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db = SQLAlchemy(app)

app.config.from_mapping(
    SECRET_KEY=os.getenv("SECRET_KEY", "dev"),
    SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///app.db"),
    OPENAI_API_KEY=os.getenv("OPENAI_API_KEY"),
    GOOGLE_SERVICE_ACCOUNT_FILE=os.path.join(BASE_DIR, "configs", "service_account.json"),
    DRIVE_FOLDER_ID=os.getenv("DRIVE_FOLDER_ID"),
    SPREADSHEET_ID=os.getenv("SPREADSHEET_ID"),
    TELEGRAM_BOT_TOKEN=os.getenv("TELEGRAM_BOT_TOKEN"),
    ADMIN_CHAT_ID=os.getenv("ADMIN_CHAT_ID"),
)

if not os.path.exists(app.config["GOOGLE_SERVICE_ACCOUNT_FILE"]):
    raise FileNotFoundError(f"Файл Google Credentials не найден: {app.config['GOOGLE_SERVICE_ACCOUNT_FILE']}")

# Инициализация Google сервисов (передаём путь к файлу учетных данных)
google_services = init_google_services(app.config["GOOGLE_SERVICE_ACCOUNT_FILE"])
app.drive_service = google_services[0]
app.sheet_service = google_services[1]

db.init_app(app)
Talisman(app, force_https=True)
CSRFProtect(app)
metrics = PrometheusMetrics(app)
admin = Admin(app, name='MyWave Admin', template_mode='bootstrap3')

csp = {
    'default-src': ["'self'", "https://stackpath.bootstrapcdn.com", "https://fonts.googleapis.com", "https://fonts.gstatic.com", "data:"],
    'script-src': ["'self'", "https://code.jquery.com"],
    'style-src': ["'self'", "'unsafe-inline'", "https://stackpath.bootstrapcdn.com", "https://fonts.googleapis.com", "https://fonts.gstatic.com"],
    'font-src': ["'self'", "https://fonts.gstatic.com"],
    'img-src': ["'self'", "data:", "https://yastatic.net", "https://fonts.gstatic.com"]
}
Talisman(app, content_security_policy=csp)

try:
    drive_service, sheet_service = init_google_services(app.config["GOOGLE_SERVICE_ACCOUNT_FILE"])
    app.drive_service = drive_service
    app.sheet_service = sheet_service
except Exception as e:
    logging.critical(f"Google API недоступен: {str(e)}")
    exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("app.log"), logging.StreamHandler()]
)

@app.before_request
def log_request():
    logging.info(f"Request: {request.method} {request.path}")

@socketio.on('message')
def handle_message(data):
    try:
        reply = f"Вы сказали: {data['message']}"
        socketio.emit('message', {"reply": reply})
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")

# Регистрация Blueprint-ов
app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(files_bp)
app.register_blueprint(calendar_bp)
app.register_blueprint(book_bp)

with app.app_context():
    drive_service, sheet_service, calendar_service = init_google_services()
    if not drive_service:
        app.logger.critical("🚨 Google Drive API не инициализирован!")
    if not sheet_service:
        app.logger.critical("🚨 Google Sheets API не инициализирован!")
    if not calendar_service:
        app.logger.critical("🚨 Google Calendar API не инициализирован!")


# Отключаем CSRF для blueprint календаря
csrf.exempt(calendar_bp)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route("/")
def index():
    return render_template("index.html")

@app.route('/chat', methods=['POST'])
def chat_handler():
    data = request.get_json()
    if not data or "message" not in data:
        return jsonify({"error": "Сообщение обязательно"}), 400
    try:
        reply = f"Вы сказали: {data['message']}"
        return jsonify({"reply": reply})
    except Exception as e:
        logging.error(f"Chat error: {str(e)}")
        return jsonify({"error": "Ошибка сервера"}), 500

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({"error": "Файл не предоставлен"}), 400
    try:
        file = request.files['file']
        file.save(f"./uploads/{file.filename}")
        return jsonify({"file_id": file.filename, "status": "success"})
    except Exception as e:
        logging.error(f"Upload error: {str(e)}")
        return jsonify({"error": "Ошибка загрузки файла"}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    socketio.run(app, debug=True)
    app.run(debug=True)
