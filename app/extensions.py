from flask_socketio import SocketIO
from flask import request
import os
from flask_wtf import CSRFProtect
from flask_wtf.csrf import validate_csrf, ValidationError as CSRFValidationError
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restx import Api
from flask_caching import Cache
from prometheus_flask_exporter import PrometheusMetrics
from flask_sqlalchemy import SQLAlchemy

# Flask-Limiter (optional, for rate limiting)
# Явный storage_uri=memory:// убирает предупреждение «no storage specified» в dev.
# Production: RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0 (или совместимый backend).
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    _ratelimit_uri = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri=_ratelimit_uri,
    )
except ImportError:
    limiter = None

socketio = SocketIO(
    cors_allowed_origins=[
        "https://mywavetreaning.ru",
        "https://www.mywave.ru",
        "http://127.0.0.1:5000",
        "http://localhost:5000"
    ],
    async_mode='eventlet',
    logger=True,
    engineio_logger=True,
    ping_timeout=60
)
csrf = CSRFProtect()
migrate = Migrate()
api = Api(doc='/swagger/')
cache = Cache()
db = SQLAlchemy()

def init_websocket(app):
    """
    Socket.IO: CSRF при connect (токен в auth) и дублирующая проверка по событию message
    (клиент шлёт csrf_token после connect). Обработчики регистрируются один раз на приложение.
    Текст ответов чата по сокету не передаётся — только HTTP POST /chat/api.
    """
    @socketio.on('connect')
    def handle_connect(auth=None):
        csrf_token = None
        if isinstance(auth, dict):
            csrf_token = auth.get('csrf_token')
        if not csrf_token:
            app.logger.info("Socket connect: нет CSRF в auth, ожидаем message с токеном")
            return True
        try:
            validate_csrf(csrf_token)
            app.logger.info("WebSocket connection accepted with valid CSRF token")
            return True
        except CSRFValidationError:
            app.logger.warning("WebSocket connection rejected: Invalid CSRF token")
            return False
        except Exception as e:
            app.logger.error("Error validating CSRF token: %s", e)
            return False

    @socketio.on('message')
    def handle_socket_message(message):
        """Подтверждение CSRF из первого message (см. static/js/socket-client.js)."""
        try:
            if isinstance(message, dict) and 'csrf_token' in message:
                try:
                    validate_csrf(message['csrf_token'])
                    app.logger.debug("CSRF validated from socket message")
                    return {'status': 'authenticated'}
                except CSRFValidationError:
                    app.logger.warning("Invalid CSRF token in socket message")
                    return {'status': 'error', 'message': 'Invalid CSRF token'}
        except Exception as e:
            app.logger.error("Error processing socket message: %s", e)
            return {'status': 'error', 'message': 'Internal error'}
        return {'status': 'ok'}

    socketio.init_app(app)
    return socketio

def init_extensions(app, db=None):
    # Инициализация CSRF защиты
    csrf.init_app(app)

    # Flask-Limiter (rate limiting)
    if limiter is not None:
        limiter.init_app(app)
        uri = os.getenv("RATELIMIT_STORAGE_URI", "memory://")
        if uri.startswith("memory") and os.getenv("FLASK_ENV", "").lower() == "production":
            app.logger.warning(
                "Flask-Limiter: in-memory storage in production — set RATELIMIT_STORAGE_URI "
                "(e.g. redis://127.0.0.1:6379/0) for consistent limits across workers"
            )
        elif uri.startswith("memory"):
            app.logger.info(
                "Flask-Limiter: storage_uri=memory:// (OK for local/dev). "
                "Prod: RATELIMIT_STORAGE_URI=redis://..."
            )
    
    # Инициализация CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": ["https://mywavetreaning.ru", "https://www.mywave.ru"]}},
        supports_credentials=True
    )
    
    # Инициализация API
    api.init_app(app)
    
    # Инициализация кэширования
    try:
        from app.config.cache_config import CACHE_CONFIG
        cache.init_app(app, config=CACHE_CONFIG)
        app.app = app  # Fix for cache.app attribute
        app.logger.info("Cache initialized successfully")
    except Exception as e:
        app.logger.error(f"Failed to initialize cache: {e}")
        # Fallback к базовой конфигурации кэша
        cache.init_app(app, config={'CACHE_TYPE': 'SimpleCache'})
        app.app = app  # Fix for cache.app attribute
    
    # Инициализация Prometheus метрик
    try:
        metrics = PrometheusMetrics(app)
    except ValueError as ve:
        # This typically says PROMETHEUS_MULTIPROC_DIR must be set
        app.logger.warning(f"Prometheus multiprocess not configured: {ve}")
        try:
            # Attempt a non-multiprocess fallback (single-process metrics)
            metrics = PrometheusMetrics(app, export_defaults=False)
        except Exception:
            # As a last resort, skip metrics but continue startup
            app.logger.exception("Failed to initialize PrometheusMetrics; continuing without metrics")
            metrics = None

    # Optional Sentry initialization (safe - won't break startup if SDK missing)
    try:
        sentry_dsn = app.config.get('SENTRY_DSN') or os.getenv('SENTRY_DSN')
        if sentry_dsn:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.flask import FlaskIntegration

                sentry_sdk.init(
                    dsn=sentry_dsn,
                    integrations=[FlaskIntegration()],
                    traces_sample_rate=float(app.config.get('SENTRY_TRACES_SAMPLE_RATE', 0.1)),
                    release=app.config.get('RELEASE')
                )
                app.logger.info('Sentry initialized')
            except Exception as e:
                # If sentry_sdk isn't installed or init fails, warn but continue
                app.logger.warning(f"Sentry init failed or sentry-sdk missing: {e}")
    except Exception:
        # Defensive: don't let monitoring setup crash the app
        app.logger.exception('Unexpected error during optional Sentry init; continuing')
    
    # Инициализация базы данных
    if db is not None:
        migrate.init_app(app, db)
        try:
            from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
            GunicornPrometheusMetrics(app, group_by='endpoint')
        except ImportError:
            pass
    
    # Настройка заголовков кэширования
    @app.after_request
    def add_cache_headers(response):
        if request.endpoint == 'static':
            # Статические файлы кэшируются на год
            response.cache_control.max_age = 31536000  # 1 год
            response.cache_control.public = True
        elif request.endpoint and 'images.' in request.endpoint:
            # Изображения кэшируются на неделю
            response.cache_control.max_age = 604800  # 7 дней
            response.cache_control.public = True
        return response
