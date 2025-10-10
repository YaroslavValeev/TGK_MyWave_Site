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
    socketio.run(app, debug=True, host='0.0.0.0', port=5000)
