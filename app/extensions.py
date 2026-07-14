from flask_socketio import SocketIO
from flask import request, redirect, url_for
import os
from flask_login import LoginManager
from flask_wtf import CSRFProtect
from flask_wtf.csrf import validate_csrf, ValidationError as CSRFValidationError
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restx import Api
from flask_caching import Cache
from prometheus_flask_exporter import PrometheusMetrics
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlsplit

# Flask-Limiter (optional, for rate limiting)
# Явный storage_uri=memory:// убирает предупреждение «no storage specified» в dev.
# Production: RATELIMIT_STORAGE_URI=redis://127.0.0.1:6379/0 (или совместимый backend).
try:
    from flask_limiter import Limiter
    from flask_limiter.errors import RateLimitExceeded

    from app.config.rate_limit_config import RateLimitConfig
    from app.services.rate_limit import (
        build_rate_limit_response,
        get_client_ip,
        should_skip_global_rate_limit,
    )

    limiter = Limiter(
        key_func=get_client_ip,
        default_limits=list(RateLimitConfig.DEFAULT_LIMITS),
        default_limits_exempt_when=should_skip_global_rate_limit,
        storage_uri=RateLimitConfig.STORAGE_URI,
        enabled=RateLimitConfig.ENABLED,
    )
except ImportError:
    limiter = None
    RateLimitExceeded = None  # type: ignore[misc, assignment]


def _origin_from_url(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return ""
    parsed = urlsplit(raw if "://" in raw else f"https://{raw}")
    if not parsed.netloc:
        return ""
    return f"{parsed.scheme or 'https'}://{parsed.netloc}"


def _public_http_origins() -> list[str]:
    out: list[str] = []
    candidates = [
        os.getenv("PUBLIC_BASE_URL"),
        os.getenv("BASE_URL"),
        os.getenv("SITE_BASE_URL"),
    ]
    server_name = (os.getenv("SERVER_NAME") or os.getenv("DOMAIN") or "").strip()
    if server_name:
        candidates.append(f"https://{server_name}")
        if not server_name.startswith("www."):
            candidates.append(f"https://www.{server_name}")
    if not any((candidate or "").strip() for candidate in candidates):
        candidates.extend([
            "https://mywavewake.ru",
            "https://www.mywavewake.ru",
        ])
    for candidate in candidates:
        origin = _origin_from_url(candidate or "")
        if origin and origin not in out:
            out.append(origin)
    return out


def _socketio_cors_origins() -> list[str]:
    """Те же хосты, что и в main.py при переборе портов 5000–5010 — иначе Engine.IO режет Origin."""
    out = _public_http_origins()
    for port in range(5000, 5012):
        out.append(f"http://127.0.0.1:{port}")
        out.append(f"http://localhost:{port}")
    extra = (os.getenv("SOCKETIO_CORS_EXTRA_ORIGINS") or "").strip()
    for part in extra.split(","):
        p = part.strip()
        if p and p not in out:
            out.append(p)
    return out


def _make_socketio() -> SocketIO:
    _si_debug = (os.getenv("SOCKETIO_LOG_VERBOSE") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    _kwargs: dict = {
        "cors_allowed_origins": _socketio_cors_origins(),
        "async_mode": "eventlet",
        "logger": _si_debug,
        "engineio_logger": _si_debug,
        "ping_timeout": 60,
    }
    # Multi-worker / horizontal scaling: задать SOCKETIO_MESSAGE_QUEUE=redis://...
    _mq = (os.getenv("SOCKETIO_MESSAGE_QUEUE") or "").strip()
    if _mq:
        _kwargs["message_queue"] = _mq
    return SocketIO(**_kwargs)


socketio = _make_socketio()
csrf = CSRFProtect()
login_manager = LoginManager()
login_manager.session_protection = "strong"
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

    # Flask-Login: сессии, user_loader, редирект на /admin/login для защищённых /admin/* (кроме логина)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"

    @login_manager.user_loader
    def load_user(user_id):
        if user_id is None:
            return None
        from app.database.models import User
        try:
            return User.query.get(int(user_id))
        except (TypeError, ValueError):
            return None

    @login_manager.unauthorized_handler
    def _unauthorized():
        p = (request.path or "")
        if p.startswith("/admin") and not p.startswith("/admin/login"):
            return redirect(url_for("auth.login", next=request.url))
        return redirect(url_for("auth.login", next=request.url))

    # Flask-Limiter (rate limiting)
    if limiter is not None:
        limiter.init_app(app)
        uri = app.config.get("RATELIMIT_STORAGE_URI") or os.getenv("RATELIMIT_STORAGE_URI", "memory://")
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

        if RateLimitExceeded is not None:
            @app.errorhandler(RateLimitExceeded)
            def _handle_rate_limit_exceeded(exc):
                return build_rate_limit_response(exc)
    
    # Инициализация CORS
    CORS(
        app,
        resources={r"/api/*": {"origins": _public_http_origins()}},
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
    
    # Инициализация Prometheus: HTTP-метрики, endpoint /metrics отдаёт app/routes/metrics_api.py
    # (два route на /metrics ломают отдачу — auto-path отключаем).
    try:
        metrics = PrometheusMetrics(
            app,
            path=None,
            export_defaults=True,
        )
    except ValueError as ve:
        # This typically says PROMETHEUS_MULTIPROC_DIR must be set
        app.logger.warning(f"Prometheus multiprocess not configured: {ve}")
        try:
            metrics = PrometheusMetrics(
                app,
                path=None,
                export_defaults=True,
            )
        except Exception:
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
    # Gunicorn multi-worker + PROMETHEUS_MULTIPROC_DIR: при необходимости подключить
    # GunicornInternalPrometheusMetrics (см. docs в prometheus_flask_exporter), не дублируя PrometheusMetrics.
    
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
