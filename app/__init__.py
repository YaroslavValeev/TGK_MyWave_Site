import os
from flask import Flask, render_template, send_from_directory, jsonify
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config

from app.database.models import db
from app.routes.calendar_routes import calendar_bp
from app.routes.services import services_bp
from app.routes.book import booking_bp
from app.extensions import init_extensions, init_websocket, socketio, api
from app.routes.api import api_ns

# Импорт остальных blueprint-ов
from app.routes.auth import auth_bp
from app.routes.chat import chat_bp
from app.routes.files import files_bp
from app.routes.blog import blog_bp
from app.routes.about import about_bp
from app.routes.contact import contact_bp
from app.routes.api import api_bp
from app.routes.booking_api import booking_api_bp
from app.routes.reviews import reviews_bp
from app.services.responses_api import responses_bp
from app.routes.telegram.routes import telegram_bp
from app.routes.content_calendar import bp as content_bp, get_events_by_month

# Создаем экземпляры расширений
migrate = Migrate()

from flask_wtf.csrf import CSRFProtect, generate_csrf

def create_app(config_name="development"):
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
    # If running in testing mode, set TESTING config and disable CSRF early
    if config_name and str(config_name).lower() == 'testing':
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        # Make Google calls return mocks during tests
        app.config['GOOGLE_MOCK'] = True

    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        from flask_wtf.csrf import generate_csrf
        print('CSRF endpoint registered')
        return jsonify({'csrf_token': generate_csrf()})
    
    # Инициализация CSRF защиты
    # Disable CSRF in testing mode to simplify tests that use the test client
    if app.config.get('TESTING'):
        app.config['WTF_CSRF_ENABLED'] = False
    csrf = CSRFProtect()
    csrf.init_app(app)
    
    # Обработчик CSRF ошибок
    @app.errorhandler(400)
    def handle_csrf_error(e):
        import traceback
        from flask import request
        print("=== CSRF DEBUG ===")
        print("Request headers:", dict(request.headers))
        print("Request cookies:", request.cookies)
        print("Request data:", request.get_data())
        print("Exception:", e)
        print(traceback.format_exc())
        print("==================")
        if 'CSRF' in str(e):
            return jsonify(error="CSRF token missing or invalid"), 400
        return jsonify(error=str(e)), 400

    # Добавляем CSRF токен в контекст шаблона
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf())

    # Load assistant prompt from file if present to use as CHAT_SYSTEM_PROMPT fallback
    try:
        prompt_path = os.path.join(app.root_path, 'config', 'assistant_prompt.md')
        if os.path.exists(prompt_path):
            with open(prompt_path, 'r', encoding='utf-8') as f:
                # don't overwrite if already set from environment/config file
                app.config.setdefault('CHAT_SYSTEM_PROMPT', f.read())
    except Exception:
        # non-fatal; continue without raising
        app.logger.debug('Could not load assistant prompt file, continuing without it')

    @app.route('/', endpoint='index')
    def home():
        # Временно отключаем получение событий календаря
        months = {'Июнь': [], 'Июль': [], 'Август': [], 'Сентябрь': [], 'Октябрь': []}
        return render_template('index.html', months=months)

    @app.route('/favicon.ico')
    def favicon():
        return send_from_directory(os.path.join(app.root_path, 'static'),
                                 'favicon.ico', mimetype='image/vnd.microsoft.icon')

    # CSP политика из конфига
    app.config['CSP_POLICY'] = app.config.get('CSP_POLICY')

    # debug из конфига/окружения
    app.config['DEBUG'] = os.getenv('FLASK_DEBUG', 'False') == 'True'

    # Инициализация базовых модулей
    app.config.from_object({
        "development": "config.DevelopmentConfig",
        "production": "config.ProductionConfig"
    }.get(config_name.lower(), "config.DevelopmentConfig"))

    # If running in testing mode, enforce test-friendly settings (after loading base config)
    if config_name and str(config_name).lower() == 'testing':
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        app.config['GOOGLE_MOCK'] = True

    # Сначала инициализируем базу данных
    db.init_app(app)
    migrate.init_app(app, db)

    # Затем остальные расширения
    init_extensions(app, db)
    init_websocket(app)

    # Настройка CSP с поддержкой всех необходимых сервисов
    csp = {
        'default-src': ["'self'"],
        'script-src': [
            "'self'",
            "'unsafe-eval'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://www.googletagmanager.com",
            "https://cdn.socket.io",
            "https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.7.2/socket.io.min.js",
            "https://mc.yandex.ru"
        ],
        'style-src': ["'self'", "'unsafe-eval'", "https://cdn.jsdelivr.net", "https://fonts.googleapis.com"],
        'img-src': ["'self'", "https://cdn.jsdelivr.net", "https://cdnjs.cloudflare.com", "https://www.googletagmanager.com", "data:"],
        'font-src': ["'self'", "https://cdn.jsdelivr.net", "https://fonts.gstatic.com"],
        'connect-src': [
            "'self'",
            "https://cdn.jsdelivr.net",
            "https://cdnjs.cloudflare.com",
            "https://cdn.socket.io",
            "https://api.openai.com"
        ],
        'frame-src': ["'self'", "https://cdn.jsdelivr.net", "https://calendar.google.com"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        'upgrade-insecure-requests': [],
        'manifest-src': ["'self'"],
        'media-src': ["'self'"],
    }

    # Инициализация Talisman с CSP
    # Talisman(app, content_security_policy=csp)

    # Регистрация blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(files_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(about_bp)
    app.register_blueprint(contact_bp)
    try:
        from app.routes.admin_api import admin_api_bp
        app.register_blueprint(admin_api_bp)
    except Exception:
        app.logger.exception('Could not register admin_api_bp')
    # Tours blueprint (Wake Discovery)
    try:
        from app.routes.tours import tours_bp
        app.register_blueprint(tours_bp)
    except Exception:
        app.logger.exception('Could not register tours_bp')
    app.register_blueprint(calendar_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(reviews_bp)
    app.register_blueprint(responses_bp)
    app.register_blueprint(telegram_bp)
    # payments
    try:
        from app.routes.payments import payments_bp
        app.register_blueprint(payments_bp)
    except Exception:
        app.logger.exception('Could not register payments_bp')
    app.register_blueprint(content_bp)
    app.register_blueprint(booking_api_bp)
    api.add_namespace(api_ns, path='/api')

    # Initialize telegram handlers safely (lazy init inside module)
    try:
        from app.routes.telegram.routes import init_telegram
        init_telegram()
    except Exception:
        app.logger.exception('Failed to initialize telegram handlers')
    # Register pricing and booking endpoints
    try:
        from app.routes.pricing_booking import bp as pricing_bp
        app.register_blueprint(pricing_bp)
    except Exception:
        app.logger.exception('Could not register pricing_booking blueprint')

    @app.after_request
    def add_security_headers(response):
        csp = app.config.get('CSP_POLICY', {})
        csp_header = "; ".join([
            f"{k} {' '.join(v) if isinstance(v, list) else v}" for k, v in csp.items()
        ])
        response.headers['Content-Security-Policy'] = csp_header
        return response

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify(status="ok", version=app.config.get('VERSION')), 200

    # Initialize Google Services
    with app.app_context():
        try:
            # Support setting GOOGLE_SERVICE_ACCOUNT_JSON env var (CI friendly):
            # if present, write it to GOOGLE_SERVICE_ACCOUNT_FILE before google init
            ga_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
            if ga_json:
                try:
                    target = app.config.get('GOOGLE_SERVICE_ACCOUNT_FILE')
                    with open(target, 'w', encoding='utf-8') as fh:
                        fh.write(ga_json)
                    app.logger.info('Wrote GOOGLE_SERVICE_ACCOUNT_JSON to %s', target)
                except Exception:
                    app.logger.exception('Failed to write GOOGLE_SERVICE_ACCOUNT_JSON to file')
            if not app.config.get('SPREADSHEET_ID'):
                app.logger.warning("SPREADSHEET_ID не задан в конфигурации")
                
            from app.services.google import get_google_services
            services = get_google_services()
            app.logger.info("Google services successfully initialized")
            
            # Verify access to the spreadsheet
            if app.config.get('SPREADSHEET_ID'):
                sheets_service = services[1]
                try:
                    sheets_service.spreadsheets().get(
                        spreadsheetId=app.config['SPREADSHEET_ID']
                    ).execute()
                    app.logger.info("Successfully validated access to Google Sheets")
                except Exception as e:
                    app.logger.error(f"Error accessing Google Sheet: {e}")
                    if 'invalid_grant' in str(e):
                        app.logger.error("Invalid JWT Signature. Check your service_account.json file")
                    raise
                    
        except Exception as e:
            app.logger.error(f"Failed to initialize Google services: {e}")
            if 'invalid_grant' in str(e):
                app.logger.error("Google Service Account authorization failed. Please check your service_account.json file")

    return app
