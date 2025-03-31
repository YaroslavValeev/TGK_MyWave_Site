from flask import Flask
from app.routes.calendar_routes import calendar_bp

app = Flask(__name__)
app.register_blueprint(calendar_bp)

# Импорт остальных blueprint-ов
from app.routes.auth import bp as auth_bp
from app.routes.chat import chat_bp
from app.routes.files import bp as files_bp

app.register_blueprint(auth_bp)
app.register_blueprint(chat_bp)
app.register_blueprint(files_bp)

@app.after_request
def add_security_headers(response):
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.socket.io https://www.googletagmanager.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https://www.googletagmanager.com;"
    )
    return response

@app.after_request
def set_csp(response):
    csp_policy = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://www.googletagmanager.com https://code.jquery.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "img-src 'self' data: https://www.googletagmanager.com; "
        "font-src 'self' https://fonts.gstatic.com;"
    )
    response.headers['Content-Security-Policy'] = csp_policy
    return response
