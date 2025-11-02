import os
from app import create_app, socketio
from flask import send_from_directory

# Настройка Prometheus
prometheus_dir = os.path.join(os.path.dirname(__file__), 'prometheus_multiproc')
if not os.path.exists(prometheus_dir):
    os.makedirs(prometheus_dir)
os.environ['PROMETHEUS_MULTIPROC_DIR'] = prometheus_dir

app = create_app()

# [CSP/nonce] вставить сразу после строки: app = create_app()
import secrets
from flask import g, request


@app.before_request
def _gen_csp_nonce():
    # Генерируем nonce на каждый запрос и прокидываем в g
    g.csp_nonce = secrets.token_urlsafe(16)


@app.after_request
def _set_csp(response):
    # Строгая CSP: inline-скрипты разрешены только с nonce
    nonce = getattr(g, "csp_nonce", "")
    csp = (
        "default-src 'self'; "
        f"script-src 'self' 'nonce-{nonce}' https://www.googletagmanager.com https://www.google-analytics.com; "
        "connect-src 'self' https://www.google-analytics.com https://*.googleapis.com; "
        "img-src 'self' data: https://www.google-analytics.com; "
        "style-src 'self' 'unsafe-inline'; "  # временно допускаем inline-стили для совместимости
        "font-src 'self' data:; "
        "frame-ancestors 'self'; base-uri 'self'; object-src 'none'; form-action 'self'"
    )
    response.headers["Content-Security-Policy"] = csp
    return response

# (sitemap and analytics routes are provided by the application factory in app/__init__.py)


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
