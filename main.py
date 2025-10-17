import os
from app import create_app, socketio
from flask import send_from_directory

# Настройка Prometheus
prometheus_dir = os.path.join(os.path.dirname(__file__), 'prometheus_multiproc')
if not os.path.exists(prometheus_dir):
    os.makedirs(prometheus_dir)
os.environ['PROMETHEUS_MULTIPROC_DIR'] = prometheus_dir

app = create_app()

if __name__ == '__main__':
    # Pre-check: if port is in use, fail fast with a clear message to avoid WinError traceback
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        result = s.connect_ex(('127.0.0.1', 5000))
        if result == 0:
            print('Port 5000 is already in use. Please stop the other process or change the port.')
            raise SystemExit(1)
    finally:
        s.close()

    # Disable the reloader to avoid double-binding the socket when using eventlet
    socketio.run(app, debug=True, host='0.0.0.0', port=5000, use_reloader=False)
