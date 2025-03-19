import os
import logging
import warnings
from flask import Flask, render_template, request, jsonify, current_app, send_from_directory
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
from app.routes.calendar_routes import calendar_bp
from app.services.google import init_google_services
from app.utils import notify_admin, process_chat_message  # Import the missing function
from app.database.models import User, Analytics

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
csrf = CSRFProtect(app)
app.config.from_object(Config)
app.config.from_object(DevelopmentConfig)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

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

# Отключаем предупреждение о file_cache
warnings.filterwarnings('ignore', message='file_cache is only supported with oauth2client<4.0.0')

# Регистрация SQLAlchemy на приложении
db.init_app(app)

# Если ранее вы инициализировали Talisman с force_https, лучше удалить дублирование.
# Инициализируем Talisman с обновленной настройкой Content Security Policy (CSP)
csp = {
    'default-src': ["'self'"],
    'style-src': ["'self'", "https://fonts.googleapis.com", "'unsafe-inline'"],
    'font-src': ["'self'", "https://fonts.gstatic.com"],
    'script-src': ["'self'", "'unsafe-inline'", "https://code.jquery.com"]
}
Talisman(app, content_security_policy=csp, force_https=True)

metrics = PrometheusMetrics(app)
admin = Admin(app, name='MyWave Admin', template_mode='bootstrap3')

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
app.register_blueprint(calendar_bp, url_prefix="/calendar")  # убедитесь, что этот префикс указан

with app.app_context():
    try:
        drive_service, sheet_service, calendar_service = init_google_services()
        app.drive_service = drive_service
        app.sheet_service = sheet_service
        app.calendar_service = calendar_service
    except Exception as e:
        app.logger.critical(f"Google API недоступен: {str(e)}")
        exit(1)

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
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return jsonify({"error": "Сообщение обязательно"}), 400

        message = data.get("message", "")
        # Убедитесь, что функция process_chat_message определена и корректно работает
        response = process_chat_message(message)  # Ensure this function is defined or imported
        return jsonify({"reply": response})
    except Exception as e:
        logging.exception("Ошибка при обработке запроса /chat")
        return jsonify({"error": str(e)}), 500

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

@app.route('/favicon.ico')
def favicon():
    return send_from_directory("static/images", "favicon.ico", mimetype="image/vnd.microsoft.icon")

@app.errorhandler(404)
def not_found(e):
    logging.error(f"Ошибка 404. Запрошенный URL: {request.path}")  # Добавлен лог ошибки
    return jsonify({"error": "Resource not found"}), 404

@app.errorhandler(405)
def method_not_allowed(e):
    logging.error(f"Ошибка 405. Запрошенный URL: {request.path}")  # Добавлен лог ошибки
    return jsonify({"error": "Method not allowed"}), 405

# Ensure tables are created
def init_db():
    with app.app_context():
        try:
            # Create all tables
            db.create_all()
            logging.info("✅ Database tables created successfully")
        except Exception as e:
            logging.error(f"❌ Error creating database tables: {e}")
            raise

# Initialize before running
if __name__ == "__main__":
    init_db()
    # Use production server if not in debug
    if app.debug:
        socketio.run(app, debug=True)
    else:
        # Production configuration
        socketio.run(app, 
                    host="0.0.0.0", 
                    port=5000,
                    debug=False,
                    use_reloader=False)
