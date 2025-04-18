from flask_socketio import SocketIO
from flask_wtf import CSRFProtect

socketio = SocketIO(cors_allowed_origins="*")
csrf = CSRFProtect()

def init_websocket(app):
    socketio.init_app(app)
    return socketio

def init_extensions(app):
    csrf.init_app(app)
