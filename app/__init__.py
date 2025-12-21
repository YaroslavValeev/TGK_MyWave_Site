import os
import importlib
from flask import Flask, render_template, send_from_directory, jsonify, request
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
from app.services.reviews_service import get_homepage_reviews
from app.routes.projects.wakesurf_challenge import wakesurf_challenge_bp
from app.routes.projects_safari import projects_safari_bp
from app.routes.api_safari import api_safari_bp
from app.routes.wake_industry import wake_industry_bp

# Создаем экземпляры расширений
migrate = Migrate()

from app.extensions import csrf
from flask_wtf.csrf import generate_csrf

def create_app(config_name="development"):
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        from flask_wtf.csrf import generate_csrf
        # Return CSRF token in JSON and also set it as a non-HttpOnly cookie
        # so frontend JS (XHR/fetch) can read it and send in the X-CSRFToken header.
        # Cookie name 'XSRF-TOKEN' is commonly used by clients (axios, etc.).
        token = generate_csrf()
        resp = jsonify({'csrf_token': token})
        # Set cookie attributes conservatively; respect production settings
        secure = app.config.get('SESSION_COOKIE_SECURE', False)
        samesite = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
        resp.set_cookie('XSRF-TOKEN', token, secure=secure, samesite=samesite, path='/')
        app.logger.debug('CSRF endpoint registered and cookie set')
        return resp
    
    # Инициализация CSRF защиты (используем общий экземпляр из app.extensions)
    csrf.init_app(app)
    # Разрешаем API маршруты календаря обходить CSRF (AJAX запросы отправляют токен отдельно)
    try:
        # Exempt only the booking view to allow AJAX POSTs from the client without CSRF cookie
        from app.routes.calendar_routes import book_slot as _book_slot
        csrf.exempt(_book_slot)
    except Exception:
        # Не критично, если по каким-то причинам не получится — продолжим без падения
        app.logger.debug('Could not exempt calendar_bp from CSRF')
    
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
        reviews = get_homepage_reviews()
        latest_blog = None
        try:
            from app.services.blog.store import get_latest_post
            latest_blog = get_latest_post(prefer_sheets=True)
        except Exception as e:
            app.logger.error("home: не удалось загрузить последний пост блога: %s", e)
        return render_template('index.html', months=months, reviews=reviews, latest_blog=latest_blog)

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
    app.register_blueprint(calendar_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(reviews_bp)
    app.register_blueprint(responses_bp)
    app.register_blueprint(telegram_bp)
    app.register_blueprint(content_bp)
    app.register_blueprint(booking_api_bp)
    
    # WakeSurf Challenge 2025 (feature flag controlled)
    if app.config.get("WSC2025_ENABLED", True):
        app.register_blueprint(wakesurf_challenge_bp)
        app.logger.info("WakeSurf Challenge 2025 blueprint registered")
    else:
        app.logger.info("WakeSurf Challenge 2025 disabled via WSC2025_ENABLED flag")
    
    # Wake Surf Safari 2026
    app.register_blueprint(projects_safari_bp)
    app.register_blueprint(api_safari_bp)
    app.logger.info("Wake Surf Safari 2026 blueprint registered")
    
    # Wake Industry (чек-лист для соревнований)
    app.register_blueprint(wake_industry_bp)
    app.logger.info("Wake Industry blueprint registered")

    # Optional AI layer blueprints (loaded dynamically to avoid hard failures in minimal deployments)
    try:
        app.register_blueprint(importlib.import_module("app.routes.rag_api").rag_bp)
        app.register_blueprint(importlib.import_module("app.routes.ai_concierge_safari").safari_concierge_bp)
        app.register_blueprint(importlib.import_module("app.routes.ai_concierge_challenge").challenge_concierge_bp)
        app.register_blueprint(importlib.import_module("app.routes.voice_api").voice_bp)
    except Exception:
        # Non-fatal: continue without AI layer routes
        pass
    api.add_namespace(api_ns, path='/api')

    # Целенаправленно исключаем CSRF только для обработчика бронирования календаря
    try:
        # view function name в calendar_routes.py — 'book_slot'
        view = app.view_functions.get('calendar.book_slot')
        if view:
            csrf.exempt(view)
            app.logger.info('CSRF exempt applied to calendar.book_slot')
        else:
            app.logger.debug('calendar.book_slot view not found for CSRF exemption')
    except Exception as e:
        app.logger.debug(f'Error applying CSRF exemption for calendar.book_slot: {e}')

    # Чат-виджет использует JSON POST к /api/booking (через fetch). Чтобы не ловить 400 из-за
    # несовпадения CSRF токена/сессии при динамическом обновлении токенов, исключаем этот endpoint.
    try:
        view = app.view_functions.get('booking_api.booking_entry')
        if view:
            csrf.exempt(view)
            app.logger.info('CSRF exempt applied to booking_api.booking_entry')
        else:
            app.logger.debug('booking_api.booking_entry view not found for CSRF exemption')
    except Exception as e:
        app.logger.debug(f'Error applying CSRF exemption for booking_api.booking_entry: {e}')

    # AI layer APIs are designed for JSON/file POSTs (server-to-server or fetch) and do not use
    # form submissions. Exempt them from CSRF to keep the API usable without browser state.
    for _endpoint in (
        'rag.rag_search',
        'safari_concierge.safari_chat',
        'challenge_concierge.challenge_chat',
        'voice.transcribe_and_reply',
    ):
        try:
            view = app.view_functions.get(_endpoint)
            if view:
                csrf.exempt(view)
                app.logger.info(f'CSRF exempt applied to {_endpoint}')
        except Exception:
            pass

    @app.after_request
    def add_security_headers(response):
        # Ensure XSRF-TOKEN cookie exists so websocket clients can present a CSRF token
        # even when session-backed CSRF validation is not available for the handshake.
        if not request.cookies.get('XSRF-TOKEN'):
            try:
                token = generate_csrf()
                secure = app.config.get('SESSION_COOKIE_SECURE', False)
                samesite = app.config.get('SESSION_COOKIE_SAMESITE', 'Lax')
                response.set_cookie('XSRF-TOKEN', token, secure=secure, samesite=samesite, path='/')
            except Exception:
                # Non-fatal: continue without the cookie
                pass

        csp = app.config.get('CSP_POLICY', {})
        csp_header = "; ".join([
            f"{k} {' '.join(v) if isinstance(v, list) else v}" for k, v in csp.items()
        ])
        response.headers['Content-Security-Policy'] = csp_header
        return response

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify(status="ok", version=app.config.get('VERSION')), 200

    # Initialize Google Services (optional; can be skipped via SKIP_GOOGLE_INIT=1)
    skip_google_init = os.getenv("SKIP_GOOGLE_INIT", "False").lower() in ("1", "true", "yes")
    if not skip_google_init:
        with app.app_context():
            try:
                if not app.config.get('SPREADSHEET_ID'):
                    app.logger.warning("SPREADSHEET_ID не задан в конфигурации")
                    
                from app.services.google import get_google_services
                services = get_google_services()
                app.logger.info("Google services successfully initialized")
                
                # Verify access to the spreadsheet (best-effort). In dev we prefer app to start
                # even if Google Sheets is temporarily unavailable. Log the error and continue.
                if app.config.get('SPREADSHEET_ID'):
                    sheets_service = services[1]
                    try:
                        sheets_service.spreadsheets().get(
                            spreadsheetId=app.config['SPREADSHEET_ID']
                        ).execute()
                        app.logger.info("Successfully validated access to Google Sheets")
                    except Exception as e:
                        app.logger.error(f"Error accessing Google Sheet (continuing without fail): {e}")
                        if 'invalid_grant' in str(e):
                            app.logger.error("Invalid JWT Signature. Check your service_account.json file")
                        # do not raise — continue running the app in degraded mode
                        
            except Exception as e:
                app.logger.error(f"Failed to initialize Google services: {e}")
                if 'invalid_grant' in str(e):
                    app.logger.error("Google Service Account authorization failed. Please check your service_account.json file")
    else:
        app.logger.info("SKIP_GOOGLE_INIT is set — skipping Google services initialization")

    # Регистрация CLI команд
    try:
        from app.cli.migrate_blog import migrate_blog_command
        app.cli.add_command(migrate_blog_command)
        app.logger.info("CLI command 'migrate-blog' registered")
    except Exception as e:
        app.logger.warning(f"Could not register migrate-blog CLI: {e}")
    
    try:
        from app.cli.blog_sync import blog_sync_command
        app.cli.add_command(blog_sync_command)
        app.logger.info("CLI command 'blog-sync' registered")
    except Exception as e:
        app.logger.warning(f"Could not register blog-sync CLI: {e}")

    return app
