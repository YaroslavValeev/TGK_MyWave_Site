from flask_socketio import SocketIO
from flask import request
from flask_wtf import CSRFProtect
from flask_wtf.csrf import validate_csrf, ValidationError as CSRFValidationError
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restx import Api
from prometheus_flask_exporter import PrometheusMetrics
from flask_login import LoginManager

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
login_manager = LoginManager()

def init_websocket(app):
    # Добавляем проверку CSRF токена при подключении WebSocket
    @socketio.on('connect')
    def handle_connect(auth=None):
        csrf_token = None
        # Если auth передан (Flask-SocketIO >=5.0), ищем токен там
        if auth and isinstance(auth, dict):
            csrf_token = auth.get('csrf_token')
        # Если не найден — пробуем из query string
        if not csrf_token:
            csrf_token = request.args.get('csrf_token')
        # Если не найден — пробуем из заголовка
        if not csrf_token:
            csrf_token = request.headers.get('X-CSRFToken')
        # Если не найден — пробуем из Authorization (Bearer <token> or Bearer csrf=<token>)
        if not csrf_token:
            auth_header = request.headers.get('Authorization', '')
            if auth_header:
                # Common format: 'Bearer <token>'
                parts = auth_header.split(' ')
                if len(parts) == 2 and parts[0].lower() == 'bearer':
                    candidate = parts[1]
                    # If candidate contains csrf=..., extract it
                    if 'csrf=' in candidate:
                        # e.g. csrf=token
                        kv = dict([p.split('=', 1) for p in candidate.split('&') if '=' in p])
                        csrf_token = kv.get('csrf')
                    else:
                        csrf_token = candidate
        # Если не найден — пробуем из request.auth
        if not csrf_token and hasattr(request, 'auth') and request.auth:
            csrf_token = request.auth.get('csrf_token')
        # If running in debug or explicitly allowed, accept missing/invalid CSRF for local/dev sockets
        allow_insecure = app.config.get('DEBUG', False) or app.config.get('ALLOW_WEBSOCKET_NO_CSRF', False)

        if not csrf_token:
            if allow_insecure:
                app.logger.warning("WebSocket connection accepted without CSRF token (insecure mode)")
                return True
            app.logger.error("WebSocket connection rejected: CSRF token missing")
            return False

        # Validate token (may raise ValidationError)
        try:
            validate_csrf(csrf_token)
            app.logger.info("WebSocket connection accepted with valid CSRF token")
            return True
        except CSRFValidationError as ve:
            # On dev or explicit override, accept but log a warning instead of rejecting.
            if allow_insecure:
                app.logger.warning("WebSocket CSRF validation failed but connection accepted due to DEBUG/ALLOW_WEBSOCKET_NO_CSRF: %s", str(ve))
                return True
            app.logger.error("WebSocket connection rejected: Invalid CSRF token")
            return False
        except Exception as ex:
            # Unexpected error during validation
            app.logger.exception("Unexpected error during WebSocket CSRF validation")
            if allow_insecure:
                app.logger.warning("Accepting WebSocket connection despite validation error due to DEBUG/ALLOW_WEBSOCKET_NO_CSRF")
                return True
            return False
    
    socketio.init_app(app)
    return socketio

def init_extensions(app, db=None):
    csrf.init_app(app)
    # Initialize Flask-Login
    try:
        login_manager.init_app(app)
        # provide a simple user_loader using the application's User model if available
        @login_manager.user_loader
        def load_user(user_id):
            try:
                from app.database.models import User
                return User.query.get(int(user_id))
            except Exception:
                return None
    except Exception:
        app.logger.exception('Failed to initialize LoginManager')
    CORS(
        app,
        resources={r"/api/*": {"origins": ["https://mywavetreaning.ru", "https://www.mywave.ru"]}},
        supports_credentials=True
    )
    api.init_app(app)
    metrics = PrometheusMetrics(app)
    if db is not None:
        migrate.init_app(app, db)
        try:
            from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
            GunicornPrometheusMetrics(app, group_by='endpoint')
        except ImportError:
            pass
