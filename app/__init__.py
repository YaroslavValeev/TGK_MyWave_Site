import os
from flask import Flask, render_template, send_from_directory, jsonify, g, request, url_for, make_response, current_app
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

    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        from flask_wtf.csrf import generate_csrf
        print('CSRF endpoint registered')
        return jsonify({'csrf_token': generate_csrf()})
    
    # Инициализация CSRF защиты
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

    # Сначала инициализируем базу данных
    db.init_app(app)
    migrate.init_app(app, db)

    # Затем остальные расширения
    init_extensions(app, db)
    init_websocket(app)

    # ----------------------------
    # CSP nonce: генерация на запрос и прокидка в шаблоны
    # ----------------------------
    import secrets

    @app.before_request
    def generate_csp_nonce():
        """
        Генерируем уникальный nonce для каждого запроса и сохраняем в g.csp_nonce
        Используется для безопасного inline JSON-LD в шаблонах.
        """
        g.csp_nonce = secrets.token_urlsafe(16)

    @app.context_processor
    def inject_csp_nonce():
        return {"csp_nonce": getattr(g, 'csp_nonce', '')}

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
    # Регистрация калькуляторного API (если файл есть)
    try:
        from app.routes.calculator_api import calculator_api
        app.register_blueprint(calculator_api)
    except Exception:
        # Не фатально, если блюпринт ещё не создан
        app.logger.debug('calculator_api blueprint not found or failed to import')
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
    api.add_namespace(api_ns, path='/api')

    # Exempt API blueprints from CSRF to allow programmatic API clients/tests
    try:
        csrf.exempt(api_bp)
        csrf.exempt(booking_api_bp)
    except Exception:
        app.logger.debug('Could not exempt blueprints from CSRF (maybe not needed)')

    @app.after_request
    def add_security_headers(response):
        csp = app.config.get('CSP_POLICY', {})
        # Inject nonce into script-src when available
        nonce = getattr(g, 'csp_nonce', '')
        header_parts = []
        for k, v in csp.items():
            if isinstance(v, list):
                parts = v.copy()
            else:
                parts = [v]
            if k == 'script-src' and nonce:
                # ensure nonce-... is included
                parts = [p for p in parts if p != f"'nonce-{nonce}'"]
                parts.insert(0, f"'nonce-{nonce}'")
            header_parts.append(f"{k} {' '.join(parts)}")
        csp_header = "; ".join(header_parts)
        response.headers['Content-Security-Policy'] = csp_header
        return response


    # ----------------------------
    # Дополнительные утилитные роуты: projects, sitemap, calculator, analytics log
    # ----------------------------
    from datetime import datetime

    @app.route('/projects', methods=['GET'])
    def projects_page():
        # Небольшой примитивный список проектов — шаблон отрисует грид + JSON-LD
        projects = [
            {
                'slug': 'wsc',
                'name': 'WakeSurf Challenge',
                'summary': 'Соревнование и витрина KPI для спонсоров.',
                'city': 'Moscow',
                'cover': 'images/projects/wsc/wsc-main.webp',
                'images': ['images/projects/wsc/wsc-preview-1.webp'],
                'tags': ['#MyWave']
            }
        ]
        return render_template('projects.html', projects=projects)

    @app.route('/events', methods=['GET'])
    def events_page():
        """Simple events page which provides structured data (schema.org) to the template.

        This endpoint prepares a small `events_schema` list suitable for embedding
        as JSON-LD in `events.html`. In a real app you'd map your Event model to
        this structure.
        """
        events_schema = [
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "WakeSurf Safari 2025",
                "startDate": "2025-07-01",
                "location": {"@type": "Place", "name": "Волга", "address": "Волга, Россия"},
                "image": [ url_for('static', filename='images/wakesurf-safari.webp') ],
                "description": "Эксклюзивный тур по Волге с обучением",
                "eventStatus": "https://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "url": url_for('events_page')
            },
            {
                "@context": "https://schema.org",
                "@type": "Event",
                "name": "Тренировочный кемп в Сочи",
                "startDate": "2025-12-01",
                "location": {"@type": "Place", "name": "Сочи", "address": "Сочи, Россия"},
                "image": [ url_for('static', filename='images/sochi-camp.webp') ],
                "description": "Зимние тренировки в горном регионе",
                "eventStatus": "https://schema.org/EventScheduled",
                "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
                "url": url_for('events_page')
            }
        ]
        return render_template('events.html', events=events_schema)

    @app.route('/sitemap.xml', methods=['GET'])
    def sitemap():
        lastmod = datetime.utcnow().date().isoformat()
        urls = {
            'static': ['/', '/projects', '/services', '/book', '/calculator', '/blog'],
            'project_slugs': []
        }
        xml = render_template('sitemap.xml', lastmod=lastmod, urls=urls)
        resp = make_response(xml)
        resp.headers['Content-Type'] = 'application/xml'
        return resp

    @app.route('/calculator', methods=['GET'])
    def calculator_page():
        return render_template('calculator.html')

    @app.route('/analytics/log', methods=['POST'])
    def analytics_log():
        # Приём простого JSON лога и прокидка в Google Sheets — заглушка/реализация по месту
        data = request.get_json(silent=True) or {}
        event = data.get('event', 'unknown')
        label = data.get('label', '')
        phone = data.get('phone', '')
        timestamp = datetime.utcnow().isoformat()
        # Попробуем записать событие в Google Sheets, если есть конфиг
        try:
            from app.services.google_sheets_service import append_record
            sheet_id = app.config.get('ANALYTICS_SHEET_SPREADSHEET_ID') or app.config.get('SPREADSHEET_ID')
            sheet_name = app.config.get('ANALYTICS_SHEET_NAME') or 'analytics_statistics'
            row = [timestamp, event, label, phone, request.remote_addr or '', request.headers.get('User-Agent','')]
            if sheet_id:
                append_record(sheet_id, sheet_name, row)
                app.logger.info(f"Analytics logged to sheet {sheet_name}")
            else:
                app.logger.warning("ANALYTICS_SHEET_SPREADSHEET_ID / SPREADSHEET_ID not configured; skipping sheet write")
        except Exception as e:
            app.logger.error(f"Failed to write analytics to sheet: {e}")
        return jsonify({'ok': True})

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify(status="ok", version=app.config.get('VERSION')), 200

    # Initialize Google Services (skip during testing to avoid network/auth side-effects)
    with app.app_context():
        if app.config.get('TESTING'):
            app.logger.info('TESTING mode: skipping Google services initialization')
        else:
            try:
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
