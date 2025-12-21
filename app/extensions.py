from flask_socketio import SocketIO
from flask import request
from flask_wtf import CSRFProtect
from flask_wtf.csrf import validate_csrf, ValidationError as CSRFValidationError
from flask_cors import CORS
from flask_migrate import Migrate
from flask_restx import Api
from prometheus_flask_exporter import PrometheusMetrics
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

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
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

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
        # Если не найден — пробуем из Authorization
        if not csrf_token:
            auth_header = request.headers.get('Authorization', '').split(' ')
            if len(auth_header) > 1:
                csrf_token = auth_header[1]
        # Если не найден — пробуем из request.auth
        if not csrf_token and hasattr(request, 'auth') and request.auth:
            csrf_token = request.auth.get('csrf_token')
        try:
            # Prefer cookie token if present (set by /api/csrf-token or after_request), because it is guaranteed
            # to be present in the same-origin socket handshake cookies.
            cookie_token = request.cookies.get('XSRF-TOKEN')

            # Fast-path: if client explicitly sends the same token as the cookie, accept.
            # This avoids session-backed CSRF validation issues during websocket handshake.
            if cookie_token and csrf_token and cookie_token == csrf_token:
                app.logger.info("WebSocket connection accepted (cookie token matched auth token)")
                return True

            for candidate in (cookie_token, csrf_token):
                if not candidate:
                    continue
                try:
                    validate_csrf(candidate)
                    app.logger.info("WebSocket connection accepted (validate_csrf OK)")
                    return True
                except CSRFValidationError:
                    continue

            # In debug/dev we prefer UX over strict WS CSRF validation (HTTP endpoints remain protected).
            # Note: app.debug can be True even if app.config['DEBUG'] isn't set (e.g. socketio.run(debug=True)).
            if app.debug or app.config.get('DEBUG'):
                app.logger.warning("WebSocket CSRF validation failed; allowing connection in DEBUG mode")
                return True

            app.logger.error("WebSocket connection rejected: Invalid CSRF token")
            return False
        except Exception as exc:
            # Don't crash the websocket handshake due to validation errors.
            if app.debug or app.config.get('DEBUG'):
                app.logger.warning("WebSocket CSRF check error (allowed in DEBUG): %s", exc, exc_info=True)
                return True
            app.logger.error("WebSocket CSRF check error: %s", exc, exc_info=True)
            return False
    
    socketio.init_app(app)
    return socketio

def init_extensions(app, db=None):
    csrf.init_app(app)
    CORS(
        app,
        resources={r"/api/*": {"origins": ["https://mywavetreaning.ru", "https://www.mywave.ru"]}},
        supports_credentials=True
    )
    api.init_app(app)
    limiter.init_app(app)
    try:
        # In some test environments PROMETHEUS_MULTIPROC_DIR is not set and
        # PrometheusMetrics may raise ValueError; ignore metrics in that case.
        metrics = PrometheusMetrics(app)
    except Exception:
        # skip metrics initialization in constrained/test environments
        metrics = None
    if db is not None:
        migrate.init_app(app, db)
        try:
            from prometheus_flask_exporter.multiprocess import GunicornPrometheusMetrics
            try:
                GunicornPrometheusMetrics(app, group_by='endpoint')
            except ValueError:
                # PROMETHEUS_MULTIPROC_DIR not configured for tests — skip
                app.logger.debug('PROMETHEUS_MULTIPROC_DIR missing; skipping GunicornPrometheusMetrics')
        except ImportError:
            pass
