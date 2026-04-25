# Gunicorn: production для Flask + Flask-SocketIO.
# Кодовая база на async_mode=eventlet — worker ДОЛЖЕН быть eventlet (не gevent), иначе WebSocket Engine.IO ломается.
# GeventWebSocketWorker применим только после миграции Socket.IO на gevent (отдельная задача).
#
# Запуск: gunicorn -c gunicorn.conf.py main:app
#
import os

# Для Socket.IO + in-memory: один воркер. С SOCKETIO_MESSAGE_QUEUE=redis://... можно поднять workers > 1.
workers = int(os.environ.get("GUNICORN_WORKERS", "1"))
bind = os.environ.get("GUNICORN_BIND", "0.0.0.0:5000")
worker_class = os.environ.get("GUNICORN_WORKER_CLASS", "eventlet")
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.environ.get("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.environ.get("GUNICORN_KEEPALIVE", "5"))
max_requests = int(os.environ.get("GUNICORN_MAX_REQUESTS", "0"))
max_requests_jitter = int(os.environ.get("GUNICORN_MAX_REQUESTS_JITTER", "0"))
accesslog = os.environ.get("GUNICORN_ACCESS_LOG", "-")
errorlog = os.environ.get("GUNICORN_ERROR_LOG", "-")
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")
capture_output = os.environ.get("GUNICORN_CAPTURE_OUTPUT", "true").lower() in (
    "1",
    "true",
    "yes",
)
proc_name = "mywave-web"

# Логи в файл при необходимости (на сервере: GUNICORN_ACCESS_LOG=/var/log/mywave/gunicorn_access.log)
if accesslog and accesslog not in ("-", ""):
    _d = os.path.dirname(os.path.abspath(accesslog))
    if _d:
        os.makedirs(_d, exist_ok=True)

# Prometheus multiprocess (если GUNICORN_WORKERS>1)
if workers > 1 and not os.environ.get("PROMETHEUS_MULTIPROC_DIR"):
    _base = os.path.abspath(os.path.join(os.path.dirname(__file__), "prometheus_multiproc"))
    os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", _base)
