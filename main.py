import eventlet
eventlet.monkey_patch()

import os
import errno

# Загружаем .env файл ПЕРЕД импортом приложения
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import create_app, socketio
from flask import send_from_directory

# Настройка Prometheus
prometheus_dir = os.path.join(os.path.dirname(__file__), 'prometheus_multiproc')
if not os.path.exists(prometheus_dir):
    os.makedirs(prometheus_dir)
os.environ['PROMETHEUS_MULTIPROC_DIR'] = prometheus_dir

# Включаем Google сервисы
os.environ['ENABLE_GOOGLE_SERVICES'] = 'True'

app = create_app()

# Повторный init_app: в create_app() уже вызван init_websocket() → socketio.init_app(app).
# Здесь — явное указание eventlet после monkey_patch; второй «Server initialized» в логах
# ожидаем (не баг), пока оба вызова согласованы.
try:
    socketio.init_app(app, async_mode='eventlet', logger=True, engineio_logger=True)
except Exception:
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
            print(f"[main] Пробуем порт {port}...")
            socketio.run(
                app,
                host=host,
                port=port,
                debug=False,
                use_reloader=False,
                log_output=True,
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
                print(f"[main] Порт {port} занят, пробуем следующий...")
            else:
                raise
    else:
        print("[main] Все порты 5000-5010 заняты. Освободите порт и перезапустите.")
