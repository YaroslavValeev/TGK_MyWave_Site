import os
from flask import Flask, render_template
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_talisman import Talisman
from config import Config

from app.routes.calendar_routes import calendar_bp, get_slots_for_date
from app.routes.services import bp as services_bp
from app.routes.book import booking_bp
from app.services.openai import init_openai
from app.extensions import init_extensions, init_websocket, socketio
from app.models import db

# Создаем экземпляры расширений
migrate = Migrate()

def create_app(config_name="development"):
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))

    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # 💡 Инициализация базовых модулей
    app.config.from_object({
        "development": "config.DevelopmentConfig",
        "production": "config.ProductionConfig"
    }.get(config_name.lower(), "config.DevelopmentConfig"))

    # Сначала инициализируем базу данных
    db.init_app(app)
    migrate.init_app(app, db)

    # Затем остальные расширения
    init_extensions(app)
    init_websocket(app)
    init_openai(app)  # OpenAI

    # Настройка CSP с поддержкой всех необходимых сервисов
    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-eval'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://www.googletagmanager.com",
            "https://www.google-analytics.com",
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://yandex.ru",
            "https://www.gstatic.com"
        ],
        'style-src': [
            "'self'",
            "'unsafe-inline'",
            "https://fonts.googleapis.com",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com"
        ],
        'img-src': [
            "'self'",
            "data:",
            "blob:",
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://yandex.ru",
            "https://*.yandex.net",
            "https://www.google-analytics.com",
            "https://*.gstatic.com"
        ],
        'font-src': [
            "'self'",
            "data:",
            "https://fonts.gstatic.com",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com"
        ],
        'connect-src': [
            "'self'",
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://yandex.ru",
            "https://*.yandex.ru",
            "https://*.yandex.net",
            "https://www.google-analytics.com",
            "wss:",
            "ws:",
            "https://*.google-analytics.com",
            "https://*.analytics.google.com",
            "https://*.googletagmanager.com"
        ],
        'frame-src': [
            "'self'",
            "https://www.google.com",
            "https://www.youtube.com",
            "https://www.youtube-nocookie.com",
            "https://mc.yandex.ru",
            "https://mc.yandex.com",
            "https://yandex.ru"
        ],
        'media-src': ["'self'", "data:", "blob:"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'self'"],
        'manifest-src': ["'self'"],
        'worker-src': ["'self'", "blob:"],
        'child-src': ["'self'", "blob:"]
    }

    # Создаем глобальную переменную для экземпляра Talisman
    global talisman
    talisman = Talisman(
        app,
        content_security_policy=csp,
        content_security_policy_nonce_in=['script-src'],
        force_https=False  # Отключаем force_https для локальной разработки
    )

    # Добавляем nonce в контекст шаблона
    @app.context_processor
    def inject_csp_nonce():
        nonce = talisman._get_nonce()
        return {'csp_nonce': nonce}

    # 🔌 Подключение blueprints
    from app.routes.auth import bp as auth_bp
    from app.routes.chat import bp as chat_bp
    from app.routes.files import bp as files_bp
    from app.routes.blog import blog_bp
    from app.routes.about import about_bp
    from app.routes.contact import contact_bp

    app.register_blueprint(calendar_bp, url_prefix='/api/calendar')
    app.register_blueprint(booking_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp, url_prefix="/chat")
    app.register_blueprint(files_bp)
    app.register_blueprint(blog_bp, url_prefix="/blog")
    app.register_blueprint(about_bp, url_prefix="/about")
    app.register_blueprint(contact_bp, url_prefix="/contact")

    @socketio.on('disconnect')
    def handle_disconnect():
        print('Client disconnected')

    @socketio.on('get_slots')
    def handle_get_slots(data):
        date = data.get('date')
        slots = get_slots_for_date(date)
        weekday = list(slots.keys())[0]
        emit('slots_response', {'slots': slots[weekday]})

    @app.route("/")
    def index():
        return render_template("index.html")

    return app
