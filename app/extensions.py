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

socketio = SocketIO(
    cors_allowed_origins=[
        "https://mywavetreaning.ru",
        "https://www.mywave.ru",
        "http://127.0.0.1:5000",
        "http://localhost:5000",
    ],
    async_mode="eventlet",
    logger=True,
    engineio_logger=True,
    ping_timeout=60,
)
csrf = CSRFProtect()
migrate = Migrate()
api = Api(doc="/swagger/")
cache = Cache()
db = SQLAlchemy()


def init_websocket(app):
    # Добавляем проверку CSRF токена при подключении WebSocket
    @socketio.on("connect")
    def handle_connect(auth=None):
        csrf_token = None

        # 1. Проверяем данные аутентификации из сообщения подключения
        if isinstance(auth, dict):
            csrf_token = auth.get("csrf_token")

        # 2. Проверяем первое сообщение с данными аутентификации
        @socketio.on("message")
        def handle_message(message):
            nonlocal csrf_token
            try:
                if isinstance(message, dict) and "csrf_token" in message:
                    csrf_token = message["csrf_token"]
                    try:
                        validate_csrf(csrf_token)
                        app.logger.info(f"CSRF token validated from message")
                        return {"status": "authenticated"}
                    except CSRFValidationError:
                        app.logger.warning("Invalid CSRF token in message")
                        return {"status": "error", "message": "Invalid CSRF token"}
            except Exception as e:
                app.logger.error(f"Error processing message: {e}")
                return {"status": "error", "message": "Internal error"}

        # 3. Если токен не найден, даем клиенту шанс отправить его в сообщении
        if not csrf_token:
            app.logger.info(
                "No CSRF token in initial connection, waiting for auth message"
            )
            return True

        # 4. Проверяем валидность токена
        try:
            validate_csrf(csrf_token)
            app.logger.info("WebSocket connection accepted with valid CSRF token")
            return True
        except CSRFValidationError:
            app.logger.warning("WebSocket connection rejected: Invalid CSRF token")
            return False
        except Exception as e:
            app.logger.error(f"Error validating CSRF token: {e}")
            return False

    socketio.init_app(app)
    return socketio


def init_extensions(app, db=None):
    # Инициализация CSRF защиты
    csrf.init_app(app)

    # Инициализация CORS
    CORS(
        app,
        resources={
            r"/api/*": {
                "origins": ["https://mywavetreaning.ru", "https://www.mywave.ru"]
            }
        },
        supports_credentials=True,
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
        cache.init_app(app, config={"CACHE_TYPE": "SimpleCache"})
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
            app.logger.exception(
                "Failed to initialize PrometheusMetrics; continuing without metrics"
            )
            metrics = None

    # Optional Sentry initialization (safe - won't break startup if SDK missing)
    try:
        sentry_dsn = app.config.get("SENTRY_DSN") or os.getenv("SENTRY_DSN")
        if sentry_dsn:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.flask import FlaskIntegration

                sentry_sdk.init(
                    dsn=sentry_dsn,
                    integrations=[FlaskIntegration()],
                    traces_sample_rate=float(
                        app.config.get("SENTRY_TRACES_SAMPLE_RATE", 0.1)
                    ),
                    release=app.config.get("RELEASE"),
                )
                app.logger.info("Sentry initialized")
            except Exception as e:
                # If sentry_sdk isn't installed or init fails, warn but continue
                app.logger.warning(f"Sentry init failed or sentry-sdk missing: {e}")
    except Exception:
        # Defensive: don't let monitoring setup crash the app
        app.logger.exception("Unexpected error during optional Sentry init; continuing")

    # Инициализация базы данных
    if db is not None:
        migrate.init_app(app, db)
        try:
            from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics

            GunicornPrometheusMetrics(app, group_by="endpoint")
        except ImportError:
            pass

    # Настройка заголовков кэширования
    @app.after_request
    def add_cache_headers(response):
        if request.endpoint == "static":
            # Статические файлы кэшируются на год
            response.cache_control.max_age = 31536000  # 1 год
            response.cache_control.public = True
        elif request.endpoint and "images." in request.endpoint:
            # Изображения кэшируются на неделю
            response.cache_control.max_age = 604800  # 7 дней
            response.cache_control.public = True
        return response
