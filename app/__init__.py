# Патч для DNS (необязателен для unit-тестов)
try:
    import eventlet  # type: ignore

    eventlet.monkey_patch()
except Exception:  # pragma: no cover - optional dependency
    eventlet = None  # type: ignore

# Import DNS patch
try:
    from app.patches.dns_patch import _getaddrinfo
    import socket

    socket.getaddrinfo = _getaddrinfo
except Exception:  # pragma: no cover - optional DNS hardening
    _getaddrinfo = None  # type: ignore

# Загружаем .env файл ПЕРЕД импортом конфигурации
import os
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import time
from flask import Flask, render_template, send_from_directory, jsonify, g, request, url_for, make_response, current_app
from flask_socketio import SocketIO, emit
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
from app.patches.ssl_patch import patch_ssl, with_ssl_retry

from app.database.models import db
from app.routes.calendar_routes import calendar_bp
from app.routes.services import services_bp
from app.routes.booking import booking_bp
from app.routes.admin_images import admin_images_bp
from app.extensions import init_extensions, init_websocket, socketio, api, csrf
from app.routes.api import api_ns
from app.routes.admin import bp as admin_bp

# Импорт остальных blueprint-ов
from app.routes.auth import auth_bp
from app.routes.chat import chat_bp
from app.routes.files import files_bp
from app.routes.blog import blog_bp
from app.routes.competitions import competitions_bp
from app.routes.about import about_bp
from app.routes.contact import contact_bp
from app.routes.api import api_bp
from app.routes.booking_api import booking_api_bp
from app.routes.reviews import reviews_bp
from app.services.responses_api import responses_bp
from app.routes.safari_cms_api import safari_cms_bp
from app.routes.safari import safari_bp
from app.routes.api_safari import api_safari_bp
from app.routes.shop import shop_bp
telegram_bp = None
if os.getenv("DISABLE_TELEGRAM") != "1":
    try:
        from app.routes.telegram.routes import telegram_bp
    except Exception:
        import logging
        logging.getLogger(__name__).exception('Failed to import telegram_bp; continuing without telegram support')
from app.routes.content_calendar import bp as content_bp, get_events_by_month
from app.routes.health import health_bp
from app.jinja_filters import register_jinja_filters

# Создаем экземпляры расширений
migrate = Migrate()

from flask_wtf.csrf import generate_csrf

def create_app(config_name="development"):
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates"))
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static"))
    app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

    # Применяем SSL-патч
    if patch_ssl():
        app.logger.info("SSL patch applied successfully")
    else:
        app.logger.warning("SSL patch failed to apply")

    @app.route('/api/csrf-token', methods=['GET'])
    def get_csrf_token():
        from flask_wtf.csrf import generate_csrf
        app.logger.debug("csrf-token issued")
        return jsonify({'csrf_token': generate_csrf()})
    
    # CSRF: один экземпляр — app.extensions.csrf (init в init_extensions).
    # Раньше здесь вызывался второй CSRFProtect().init_app(), из‑за чего
    # @csrf.exempt на /analytics/log не работал (exempt на «левом» экземпляре).
    
    # Обработчик CSRF ошибок
    @app.errorhandler(400)
    def handle_csrf_error(e):
        from flask import request
        if app.config.get("DEBUG") or (os.getenv("CSRF_ERROR_VERBOSE") or "").strip() in ("1", "true", "yes"):
            import traceback
            app.logger.warning(
                "CSRF/400: headers=%s cookies=%s data=%r exc=%r\n%s",
                dict(request.headers),
                dict(request.cookies),
                request.get_data(),
                e,
                traceback.format_exc(),
            )
        if 'CSRF' in str(e):
            return jsonify(error="CSRF token missing or invalid"), 400
        return jsonify(error=str(e)), 400

    # Добавляем CSRF токен в контекст шаблона
    @app.context_processor
    def inject_csrf_token():
        return dict(csrf_token=generate_csrf())

    # Системная роль для публичного чата (см. docs/CHAT_RUNTIME_AND_RELEASE.md):
    # - CHAT_BACKEND=completions или отсутствие ASSISTANT_ID → Chat Completions + CHAT_SYSTEM_PROMPT
    #   (ниже: файл assistant_prompt.md, если не задано в env).
    # - CHAT_BACKEND=auto и задан ASSISTANT_ID → сначала OpenAI Assistant API (инструкции в кабинете
    #   OpenAI, не из assistant_prompt.md); при пустом ответе — fallback на Chat Completions с
    #   CHAT_SYSTEM_PROMPT.
    # - CHAT_BACKEND=assistant_only → только Assistant API без fallback на completions.
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
        months = {'Июнь': [], 'Июль': [], 'Август': [], 'Сентябрь': [], 'Октябрь': []}
        from app.services.showcases import get_project_cards
        from app.services.service_cards import build_services_list
        from app.routes.shop import _products_with_resolved_images

        try:
            from app.routes.services import _load_services_config
            services_config = _load_services_config()
        except ImportError:
            app.logger.warning("Fallback: using inline services config")
            services_config = [
                {'service_id': 'gym', 'name': 'Запись на тренировку (Зал)', 'description': '...', 'price': '3 500 ₽', 'image_folder': 'images/Services/Gym', 'modal_id': 'modalCalendar', 'button_text': 'Подробнее / Записаться'},
                {'service_id': 'boat', 'name': 'Запись на катер', 'description': '...', 'price': '10 000 ₽', 'image_folder': 'images/Services/Boat', 'modal_id': 'modalCalendar', 'button_text': 'Подробнее / Записаться'},
                {'service_id': 'camp', 'name': 'Camp', 'description': '...', 'price': 'от 15 000 ₽', 'image_folder': 'images/Services/Camp', 'modal_id': 'modalCamp', 'button_text': 'Подробнее / Оставить заявку'},
                {'service_id': 'coach_triper', 'name': 'Тренер на выезде', 'description': '...', 'price': 'по запросу', 'image_folder': 'images/Services/CoachTriper', 'modal_id': 'modalCoachTriper', 'button_text': 'Подробнее / Оставить заявку'},
                {'service_id': 'consulting', 'name': 'Консалтинг', 'description': '...', 'price': 'по запросу', 'image_folder': 'images/Services/Consalting', 'modal_id': 'modalConsulting', 'button_text': 'Подробнее / Получить консультацию'},
            ]

        services = build_services_list(services_config, url_for)
        products = _products_with_resolved_images()
        try:
            projects = get_project_cards()
        except Exception as e:
            app.logger.warning("get_project_cards failed: %s", e)
            projects = []

        blog_preview_posts = []
        try:
            from app.services.blog.store import get_posts

            items, _ = get_posts(page=1, limit=4, prefer_sheets=True)
            blog_preview_posts = items or []
        except Exception as e:
            app.logger.warning("home: не удалось загрузить превью блога: %s", e)

        competitions_ticker = []
        try:
            from app.services.competitions.store import get_ticker_items

            competitions_ticker = get_ticker_items() or []
        except Exception as e:
            app.logger.warning("home: не удалось загрузить ticker соревнований: %s", e)

        return render_template(
            'index.html',
            months=months,
            services=services,
            products=products,
            projects=projects,
            blog_preview_posts=blog_preview_posts,
            competitions_ticker=competitions_ticker,
        )

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
        "testing": "config.TestingConfig",
        "production": "config.ProductionConfig"
    }.get(config_name.lower(), "config.DevelopmentConfig"))

    # Configure logging levels: INFO in production, DEBUG otherwise.
    import logging as _logging
    root_logger = _logging.getLogger()
    try:
        if config_name.lower() == 'production' or not app.config.get('DEBUG'):
            root_logger.setLevel(_logging.INFO)
            # Reduce verbosity of noisy libraries in production
            _logging.getLogger('httpx').setLevel(_logging.WARNING)
            _logging.getLogger('sqlalchemy.engine').setLevel(_logging.WARNING)
            _logging.getLogger('googleapiclient').setLevel(_logging.WARNING)
            _logging.getLogger('googleapiclient.discovery').setLevel(_logging.WARNING)
            _logging.getLogger('engineio').setLevel(_logging.INFO)
            _logging.getLogger('socketio').setLevel(_logging.INFO)
        else:
            root_logger.setLevel(_logging.DEBUG)
    except Exception:
        # Do not let logging configuration break app startup
        app.logger.debug('Failed to configure logging levels; continuing with defaults')

    # Safety: disable Google services by default for non-production runs to avoid
    # startup failures when local credentials are missing or invalid.
    # To enable Google services locally set the environment variable ENABLE_GOOGLE_SERVICES=1
    enable_google_env = os.getenv('ENABLE_GOOGLE_SERVICES')
    if config_name.lower() != 'production':
        if enable_google_env is None:
            app.config['ENABLE_GOOGLE_SERVICES'] = False
        else:
            app.config['ENABLE_GOOGLE_SERVICES'] = str(enable_google_env).lower() in ('1', 'true', 'yes')
    else:
        # In production, prefer explicit config or enable by default if not specified
        if enable_google_env is None:
            app.config.setdefault('ENABLE_GOOGLE_SERVICES', True)
        else:
            app.config['ENABLE_GOOGLE_SERVICES'] = str(enable_google_env).lower() in ('1', 'true', 'yes')

    # Сначала инициализируем базу данных
    db.init_app(app)
    migrate.init_app(app, db)
    # AI Gateway security defaults (can be overridden via environment variables)
    # AI_GATEWAY_API_KEYS: comma-separated API keys allowed to call the AI gateway
    raw_keys = os.getenv('AI_GATEWAY_API_KEYS') or os.getenv('AI_GATEWAY_API_KEYS'.lower())
    if raw_keys:
        app.config['AI_GATEWAY_API_KEYS'] = [k.strip() for k in raw_keys.split(',') if k.strip()]
    else:
        app.config.setdefault('AI_GATEWAY_API_KEYS', [])

    # Whether the AI gateway requires an API key. Default: False in non-production (easier testing/dev).
    require_key = os.getenv('AI_GATEWAY_REQUIRE_API_KEY')
    if require_key is None:
        # In production enable by default, otherwise keep disabled for dev/tests
        app.config['AI_GATEWAY_REQUIRE_API_KEY'] = (config_name.lower() == 'production')
    else:
        app.config['AI_GATEWAY_REQUIRE_API_KEY'] = str(require_key).lower() in ('1', 'true', 'yes')

    # Rate limiting for AI gateway (per API key). Disabled by default; enable via env.
    rate_limit_enabled = os.getenv('AI_GATEWAY_ENABLE_RATE_LIMIT')
    if rate_limit_enabled is None:
        app.config['AI_GATEWAY_ENABLE_RATE_LIMIT'] = False
    else:
        app.config['AI_GATEWAY_ENABLE_RATE_LIMIT'] = str(rate_limit_enabled).lower() in ('1', 'true', 'yes')
    # Rate limit params (count per window)
    try:
        app.config['AI_GATEWAY_RATE_LIMIT_COUNT'] = int(os.getenv('AI_GATEWAY_RATE_LIMIT_COUNT') or 60)
    except Exception:
        app.config['AI_GATEWAY_RATE_LIMIT_COUNT'] = 60
    try:
        app.config['AI_GATEWAY_RATE_LIMIT_WINDOW'] = int(os.getenv('AI_GATEWAY_RATE_LIMIT_WINDOW') or 60)
    except Exception:
        app.config['AI_GATEWAY_RATE_LIMIT_WINDOW'] = 60
    if config_name.lower() == 'testing':
        app.config['WTF_CSRF_ENABLED'] = False
        app.logger.debug('CSRF disabled for testing environment')
    # Затем остальные расширения (в т.ч. csrf.init_app)
    init_extensions(app, db)
    init_websocket(app)
    
    # Инициализация кэширования
    from app.extensions import cache
    from app.config.cache_config import CACHE_CONFIG
    cache.init_app(app, config=CACHE_CONFIG)

    # Регистрация blueprint для изображений
    from app.routes.images import images
    app.register_blueprint(images)

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
    app.register_blueprint(competitions_bp)
    app.register_blueprint(safari_bp)
    try:
        from app.routes.projects_safari import projects_safari_bp
        app.register_blueprint(projects_safari_bp)
    except Exception:
        app.logger.debug('projects_safari_bp not found or failed to import')
    try:
        from app.routes.projects.wakesurf_challenge import wakesurf_challenge_bp
        app.register_blueprint(wakesurf_challenge_bp)
        app.logger.debug('wakesurf_challenge_bp registered')
    except Exception as e:
        app.logger.warning('wakesurf_challenge_bp failed to load: %s', e, exc_info=True)
    try:
        from app.routes.wake_industry import wake_industry_bp
        app.register_blueprint(wake_industry_bp)
    except Exception:
        app.logger.debug('wake_industry_bp not found or failed to import')
    app.register_blueprint(about_bp)
    app.register_blueprint(contact_bp)
    app.register_blueprint(calendar_bp)
    app.register_blueprint(services_bp)
    app.register_blueprint(shop_bp)
    app.register_blueprint(booking_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(reviews_bp)
    app.register_blueprint(responses_bp)
    # Safari CMS API (routes, faq, sync)
    try:
        app.register_blueprint(safari_cms_bp)
    except Exception:
        app.logger.debug('safari_cms_bp not found or failed to import')
    app.register_blueprint(api_safari_bp)
    # Recommendations blueprint (optional)
    try:
        from app.routes.recommendations_api import reco_bp
        app.register_blueprint(reco_bp, url_prefix='/api')
    except Exception:
        app.logger.debug('reco_bp not found or failed to import')
    
    # CSP violations API blueprint (optional)
    try:
        from app.routes.csp_api import csp_bp
        app.register_blueprint(csp_bp, url_prefix='/api')
    except Exception:
        app.logger.debug('csp_bp not found or failed to import')
        @app.route('/api/csp-violations', methods=['POST'])
        @csrf.exempt
        def csp_violations_fallback():
            """Fallback: accept and discard to avoid 404 when csp_bp fails to load."""
            try:
                request.get_json(silent=True)
            except Exception:
                pass
            return '', 204
    # AI Gateway blueprint (optional)
    try:
        from app.routes.ai_gateway_api import ai_gateway_bp, ai_safari_bp, gateway
        # Mount the AI gateway under /api/ai/gateway for clarity
        app.register_blueprint(ai_gateway_bp, url_prefix='/api/ai/gateway')
        # Optional safari-specific AI endpoint
        try:
            app.register_blueprint(ai_safari_bp, url_prefix='/api/ai/safari')
        except Exception:
            app.logger.debug('ai_safari_bp not found or failed to import')
        # Try to register default tools for the gateway (non-fatal)
        try:
            from app.ai.register_tools import register_default_tools
            register_default_tools(app)
        except Exception:
            app.logger.debug('register_default_tools failed or not present')
        # Voice streaming handlers reuse the same gateway instance so register them lazily.
        try:
            from app.voice import register_voice_handlers
            register_voice_handlers(app, gateway=gateway)
        except Exception:
            app.logger.debug('voice handlers not registered')
    except Exception:
        app.logger.debug('ai_gateway_bp not found or failed to import')
    # Site Concierge blueprint (AI-powered concierge API)
    try:
        from app.routes.ai_concierge_api import ai_concierge_bp
        app.register_blueprint(ai_concierge_bp, url_prefix='/api/concierge')
    except Exception:
        app.logger.debug('ai_concierge_bp not found or failed to import')
    # Register telegram blueprint only if import succeeded
    if telegram_bp:
        try:
            app.register_blueprint(telegram_bp)
        except Exception:
            app.logger.exception('Failed to register telegram blueprint; continuing without telegram')
    app.register_blueprint(content_bp)
    app.register_blueprint(booking_api_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(admin_images_bp)
    app.register_blueprint(health_bp)
    
    # Payment API blueprint
    try:
        from app.routes.payments_api import init_payments_api
        init_payments_api(app)
    except Exception:
        app.logger.debug('payments_api not found or failed to import')
    
    # Metrics API blueprint
    try:
        from app.routes.metrics_api import metrics_bp
        app.register_blueprint(metrics_bp)
        app.logger.info('Metrics API initialized')
    except Exception:
        app.logger.debug('metrics_api not found or failed to import')
    
    # Analytics middleware
    try:
        from app.services.analytics_service import AnalyticsMiddleware
        AnalyticsMiddleware(app)
        app.logger.info('Analytics middleware initialized')
    except Exception:
        app.logger.debug('analytics_service not found or failed to import')
    
    api.add_namespace(api_ns, path='/api')

    # Exempt API blueprints from CSRF to allow programmatic API clients/tests
    try:
        csrf.exempt(api_bp)
        csrf.exempt(booking_api_bp)
        # Exempt AI gateway API from CSRF for programmatic clients/tests
        try:
            from app.routes.ai_gateway_api import ai_gateway_bp as _ai_bp, ai_safari_bp as _ai_safari_bp
            csrf.exempt(_ai_bp)
            csrf.exempt(_ai_safari_bp)
        except Exception:
            app.logger.debug('Could not exempt ai_gateway_bp from CSRF (maybe not registered)')
        try:
            from app.routes.ai_concierge_api import ai_concierge_bp as _ai_concierge_bp
            csrf.exempt(_ai_concierge_bp)
        except Exception:
            app.logger.debug('Could not exempt ai_concierge_bp from CSRF (maybe not registered)')
        try:
            from app.safari.routes import safari_bp as _safari_bp
            csrf.exempt(_safari_bp)
        except Exception:
            app.logger.debug('Could not exempt safari_bp from CSRF (maybe not registered)')
        csrf.exempt(api_safari_bp)
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
        from app.services.showcases import get_project_cards, get_projects_graph

        projects = get_project_cards()
        jsonld = get_projects_graph()
        return render_template('projects.html', projects=projects, showcase_graph=jsonld)

    # Явный маршрут ДО /projects/<slug> — иначе slug перехватывает
    @app.route('/projects/wakesurf-challenge-2025', methods=['GET'])
    def wakesurf_challenge_page():
        view_func = current_app.view_functions.get('wakesurf_challenge.project_page')
        if view_func:
            return view_func()
        try:
            from app.routes.projects.wakesurf_challenge import project_page
            return project_page()
        except Exception as e:
            current_app.logger.exception("wakesurf_challenge_page: %s", e)
            return "Страница проекта временно недоступна", 503

    @app.route('/projects/<slug>', methods=['GET'])
    def project_detail(slug):
        """Редирект: wake-challenge → WSC; mywave-ruza-camp → страница Ruza; остальные → /projects#slug."""
        from flask import redirect, url_for
        if slug == 'wake-challenge':
            return redirect('/projects/wakesurf-challenge-2025', code=301)
        if slug == 'wake-indusrty':
            return redirect('/projects/checklist-org', code=301)
        if slug == 'checklist-org':
            from app.services.checklist_card_art import checklist_art_url_map_for_js
            from app.services.rules_downloads import load_rules_downloads

            return render_template(
                'wake_industry/checklist.html',
                checklist_art_overrides=checklist_art_url_map_for_js(),
                rules_downloads=load_rules_downloads(url_for),
            )
        if slug == 'mywave-ruza-camp':
            from app.services.showcases import get_showcase
            sc = get_showcase('mywave_ruza_camp')
            if sc:
                return render_template('projects/ruza_camp.html', showcase=sc)
        return redirect(url_for('projects_page', _anchor=slug))

    @app.route('/events', methods=['GET'])
    def events_page():
        from app.services.showcases import get_events_schema, get_event_cards

        events_schema = get_events_schema()
        cards = get_event_cards()
        return render_template('events.html', events=events_schema, event_cards=cards)

    @app.route('/sitemap.xml', methods=['GET'])
    def sitemap():
        lastmod = datetime.utcnow().date().isoformat()
        project_slugs = []
        try:
            from app.services.showcases import get_project_cards
            for p in get_project_cards():
                url = p.get('url', '')
                if url.startswith('/projects/'):
                    slug = url.replace('/projects/', '', 1).split('#')[0]
                    if slug and slug not in project_slugs:
                        project_slugs.append(slug)
        except Exception:
            pass
        urls = {
            'static': ['/', '/projects', '/services', '/book', '/calculator', '/blog'],
            'project_slugs': project_slugs
        }
        xml = render_template('sitemap.xml', lastmod=lastmod, urls=urls)
        resp = make_response(xml)
        resp.headers['Content-Type'] = 'application/xml'
        return resp

    @app.route('/calculator', methods=['GET'])
    def calculator_page():
        return render_template('calculator.html')

    @app.route('/analytics/log', methods=['POST'])
    @csrf.exempt
    def analytics_log():
        """Fire-and-forget: всегда возвращает 200, чтобы не ломать UX клиента."""
        try:
            data = request.get_json(silent=True) or {}
            event = data.get('event', 'unknown')
            label = data.get('label', '')
            phone = data.get('phone', '')
            showcase_id = data.get('showcase_id')
            channel = data.get('channel') or data.get('source') or 'web'
            trip_date = data.get('trip_date')
            timestamp = datetime.utcnow().isoformat()
            meta = data.get('meta') or {}
            if not isinstance(meta, dict):
                meta = {'payload': meta}
            if showcase_id:
                meta['showcase_id'] = showcase_id
            if channel:
                meta['channel'] = channel
            if trip_date:
                meta['trip_date'] = trip_date

            try:
                from app.services.google_sheets_service import log_analytics_event
                sheet_id = app.config.get('ANALYTICS_SHEET_SPREADSHEET_ID') or app.config.get('SPREADSHEET_ID')
                payload = {
                    'event': event,
                    'context': data.get('context') or label or '',
                    'user_key': data.get('user_key') or data.get('user') or '',
                    'rule_id': data.get('rule_id', ''),
                    'item_id': data.get('item_id', ''),
                    'type': data.get('type', '') or channel,
                    'meta': meta,
                    'ip': request.remote_addr or '',
                    'user_agent': request.headers.get('User-Agent', '')
                }
                if sheet_id:
                    _ok = log_analytics_event(payload, spreadsheet_id=sheet_id)
                    if _ok:
                        app.logger.info('Analytics logged via log_analytics_event')
                    else:
                        app.logger.warning('Analytics log_analytics_event did not persist (see google_sheets logs)')
            except Exception:
                try:
                    from app.services.google_sheets_service import append_record
                    sheet_id = app.config.get('ANALYTICS_SHEET_SPREADSHEET_ID') or app.config.get('SPREADSHEET_ID')
                    sheet_name = app.config.get('ANALYTICS_SHEET_NAME') or 'analytics_statistics'
                    row = [timestamp, event, label, phone, request.remote_addr or '', request.headers.get('User-Agent','')]
                    if sheet_id:
                        append_record(sheet_id, sheet_name, row)
                        app.logger.info(f"Analytics logged to sheet {sheet_name} (fallback)")
                except Exception as e:
                    app.logger.error(f'Failed to write analytics: {e}')
        except Exception as e:
            app.logger.warning(f'analytics/log parse error: {e}')
        return jsonify({'ok': True}), 200

    # Global exception handler: report to Sentry (if configured) and trigger a Telegram alert
    # It's defensive: HTTPExceptions are re-raised so Flask can handle them normally.
    from werkzeug.exceptions import HTTPException

    @app.errorhandler(Exception)
    def handle_unexpected_exception(e):
        if isinstance(e, HTTPException):
            # Let Flask handle HTTPExceptions (e.g., 404/400) as usual
            return e

        # Log locally
        app.logger.exception('Unhandled exception caught')

        try:
            from app.services.monitoring import report_exception

            report_exception(
                e,
                {
                    'path': request.path,
                    'method': request.method,
                    'endpoint': request.endpoint,
                },
            )
        except Exception:
            app.logger.debug('Failed to report exception via monitoring stack')

        return jsonify(error='internal server error'), 500

    # Initialize Google Services (disabled by default for local runs to avoid network/auth side-effects)
    # To enable in production set app.config['ENABLE_GOOGLE_SERVICES'] = True
    with app.app_context():
        enable_google = app.config.get('ENABLE_GOOGLE_SERVICES', False)
        if not enable_google:
            app.logger.info('Google services initialization is disabled (ENABLE_GOOGLE_SERVICES not set).')
        else:
            # proceed with the existing initialization (kept defensive)
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
                        # do not raise here to avoid breaking app startup

            except Exception as e:
                app.logger.error(f"Failed to initialize Google services: {e}")
                if 'invalid_grant' in str(e):
                    app.logger.error("Google Service Account authorization failed. Please check your service_account.json file")

    try:
        from app.services.openai_runtime_config import log_openai_chat_config_startup

        log_openai_chat_config_startup(app)
    except Exception as e:
        app.logger.debug("OpenAI chat runtime config log skipped: %s", e)

    register_jinja_filters(app)

    return app


    # NOTE: The following global exception handler is added after app construction
    # to capture unhandled exceptions, forward them to Sentry (if configured)
    # and trigger a lightweight Telegram monitoring alert without blocking request
    # processing. This handler is defensive and will not raise if monitoring
    # services are missing.

    # (kept below return for visual grouping in file; Flask will register handlers
    # during app creation because create_app executes this module's code.)
