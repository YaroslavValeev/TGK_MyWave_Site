import eventlet

eventlet.monkey_patch()

import os

# Загружаем .env файл ПЕРЕД импортом приложения
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

from app import create_app, socketio
from flask import send_from_directory

# Настройка Prometheus
prometheus_dir = os.path.join(os.path.dirname(__file__), "prometheus_multiproc")
if not os.path.exists(prometheus_dir):
    os.makedirs(prometheus_dir)
os.environ["PROMETHEUS_MULTIPROC_DIR"] = prometheus_dir

# Включаем Google сервисы
os.environ["ENABLE_GOOGLE_SERVICES"] = "True"

app = create_app()

# Ensure SocketIO is initialized with eventlet async mode after monkey patching
try:
    # socketio is provided by the app package (from app.extensions)
    socketio.init_app(app, async_mode="eventlet", logger=True, engineio_logger=True)
except Exception:
    # If socketio was already initialized inside create_app(), ignore
    pass

# [CSP/nonce] вставить сразу после строки: app = create_app()
import secrets
from flask import g, request


@app.before_request
def _gen_csp_nonce():
    # Генерируем nonce на каждый запрос и прокидываем в g
    g.csp_nonce = secrets.token_urlsafe(16)


@app.after_request
def _set_csp(response):
    # Разрешаем только собственные скрипты + JSON-LD с nonce
    nonce = getattr(g, "csp_nonce", "")
    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://www.googletagmanager.com https://www.google-analytics.com https://cdnjs.cloudflare.com https://cdn.jsdelivr.net https://mc.yandex.ru https://mc.yandex.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "img-src 'self' data: https://www.google-analytics.com https://mc.yandex.ru https://mc.yandex.com; "
        "connect-src 'self' https://www.google-analytics.com https://*.googleapis.com https://cdn.socket.io https://api.openai.com https://mc.yandex.com https://mc.yandex.ru wss://mc.yandex.com wss://mc.yandex.ru; "
        "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "frame-src 'self' https://calendar.google.com https://mc.yandex.com https://mc.yandex.ru; "
        "object-src 'none'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "upgrade-insecure-requests; "
        "manifest-src 'self'; "
        "media-src 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    return response


# [Sitemap] добавить роут
from flask import render_template, make_response, request, url_for
from datetime import datetime

# Note: sitemap route is provided by `app.create_app()` (app/__init__.py).
# Avoid redefining it here to prevent endpoint name collisions.

# [Analytics] запись в лист "Analitycs" таблицы ADMIN_TG_BOT
from flask import jsonify, current_app
import json


@app.route("/api/analytics/event", methods=["POST"])
def analytics_event():
    payload = request.get_json(force=True) or {}
    # Запись событий модалки и GA
    return {"ok": True}


# Note: analytics_log route is implemented in `app.create_app()` (app/__init__.py).
# To avoid duplicate endpoint registration we rely on the implementation there.

if __name__ == "__main__":
    # Run with eventlet; disable the Flask reloader to avoid multiple processes
    try:
        socketio.run(
            app,
            host="0.0.0.0",
            port=5000,
            debug=False,
            use_reloader=False,
            log_output=True,
        )
    except Exception as e:
        print(f"⚠️ SocketIO run failed: {e}")
        print("Falling back to standard Flask run...")
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
