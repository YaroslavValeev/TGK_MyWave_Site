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
os.environ.setdefault('PROMETHEUS_MULTIPROC_DIR', prometheus_dir)

# Не перетираем production env: включаем Google сервисы только если оператор не задал иное.
os.environ.setdefault('ENABLE_GOOGLE_SERVICES', 'True')

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
# CSP и nonce задаются только в create_app() из CSP_POLICY (config.py); дубликат здесь ломал предсказуемость.

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
