import eventlet
eventlet.monkey_patch()

import os
import errno
import sys
import logging

# Консоль Windows часто буферизует stdout — строки логов могут «не появляться» до переполнения буфера.
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except Exception:
        pass

# Загружаем .env файл ПЕРЕД импортом приложения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app, socketio
from flask import send_from_directory

_log = logging.getLogger("main")

# Настройка Prometheus
prometheus_dir = os.path.join(os.path.dirname(__file__), 'prometheus_multiproc')
if not os.path.exists(prometheus_dir):
    os.makedirs(prometheus_dir)
os.environ['PROMETHEUS_MULTIPROC_DIR'] = prometheus_dir

# Включаем Google сервисы
os.environ['ENABLE_GOOGLE_SERVICES'] = 'True'

def _flask_config_name() -> str:
    v = (os.getenv("FLASK_CONFIG") or os.getenv("FLASK_ENV") or "development").strip().lower()
    if v in ("production", "prod"):
        return "production"
    if v in ("testing", "test"):
        return "testing"
    return "development"


app = create_app(_flask_config_name())
application = app  # gunicorn / uwsgi
_log_file_hint = os.path.abspath(os.path.join(os.path.dirname(__file__), "logs", "app.log"))
_log.info("Приложение загружено; логи: %s", _log_file_hint)
# init_websocket() уже вызван в create_app() — повторный socketio.init_app не нужен

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

@app.route('/api/analytics/event', methods=['POST'])
def analytics_event():
    payload = request.get_json(force=True) or {}
    # Запись событий модалки и GA
    return {"ok": True}
# Note: analytics_log route is implemented in `app.create_app()` (app/__init__.py).
# To avoid duplicate endpoint registration we rely on the implementation there.

if __name__ == '__main__':
    host = '0.0.0.0'
    for port in range(5000, 5011):
        try:
            _log.info("Пробуем порт %s (локальный dev; production: gunicorn -c gunicorn.conf.py main:app)", port)
            socketio.run(
                app,
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                log_output=_log.isEnabledFor(logging.DEBUG),
                allow_unsafe_werkzeug=True,
            )
            break
        except OSError as e:
            # Windows: WinError 10048 (WSAEADDRINUSE); локализованное сообщение не совпадает с EN-текстом.
            addr_in_use = (
                e.errno == errno.EADDRINUSE
                or getattr(e, "winerror", None) == 10048
                or "address already in use" in str(e).lower()
                or "уже используется" in str(e).lower()
            )
            if addr_in_use:
                _log.warning("Порт %s занят, следующий", port)
            else:
                raise
    else:
        _log.error("Порты 5000-5010 заняты; освободите порт.")
