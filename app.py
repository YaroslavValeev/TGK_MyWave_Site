"""Entrypoint for local development.

We set environment defaults and apply eventlet monkey-patch early, before importing
any application code. This ensures the eventlet async driver is available for
Flask-SocketIO and prevents startup errors from Prometheus multiprocess exporter.
"""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Ensure Prometheus multiproc dir exists and is set in environment
PROMETHEUS_DIR = os.path.abspath('./prometheus_multiproc')
os.environ['PROMETHEUS_MULTIPROC_DIR'] = PROMETHEUS_DIR
try:
    os.makedirs(PROMETHEUS_DIR, exist_ok=True)
    logger.info(f"Prometheus multiproc directory configured: {PROMETHEUS_DIR}")
except Exception as e:
    logger.error(f"Failed to create Prometheus directory: {e}")
    sys.exit(1)

# Apply eventlet monkey patch early
try:
    import eventlet
    eventlet.monkey_patch()
    logger.info("Successfully applied eventlet monkey patch")
except ImportError as e:
    logger.error(f"Failed to import eventlet - WebSocket support will be limited: {e}")
    sys.exit(1)

from flask import Blueprint, request, jsonify, render_template
from flask_socketio import emit
from websocket_handler import ws_handler
from app import create_app

# API Blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route("/chat", methods=["POST"])
def chat():
    """Chat API endpoint"""
    try:
        data = request.get_json()
        message = data.get("message", "")
        return jsonify(reply=f"Вы сказали: {message}")
    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return jsonify(error="Internal server error"), 500

@api_bp.route("/upload", methods=["POST"])
def upload():
    """File upload API endpoint"""
    try:
        if 'file' not in request.files:
            return jsonify(error="Нет файла в запросе"), 400
        file = request.files["file"]
        upload_dir = os.path.abspath("./uploads")
        os.makedirs(upload_dir, exist_ok=True)
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)
        logger.info(f"File uploaded: {file_path}")
        return jsonify(file_id=file.filename)
    except Exception as e:
        logger.error(f"Upload API error: {e}")
        return jsonify(error="Failed to upload file"), 500

@api_bp.route("/book", methods=["POST"])
def book():
    """Booking API endpoint"""
    try:
        booking_data = request.get_json()
        # TODO: Add actual booking logic
        return jsonify(success=True)
    except Exception as e:
        logger.error(f"Booking API error: {e}")
        return jsonify(error="Failed to process booking"), 500

@api_bp.errorhandler(404)
def page_not_found(e):
    """404 error handler"""
    return render_template('404.html'), 404

# Initialize Telegram bot if possible
def setup_telegram():
    """Initialize Telegram bot with error handling"""
    try:
        from telegram.ext import ApplicationBuilder
        from config import TELEGRAM_TOKEN
        
        if not TELEGRAM_TOKEN:
            logger.warning("TELEGRAM_TOKEN not set - skipping Telegram integration")
            return None
            
        app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        logger.info("Telegram bot initialized successfully")
        return app
    except Exception as e:
        logger.error(f"Failed to initialize Telegram bot (httpx version issue?): {e}")
        return None

if __name__ == '__main__':
    # Create Flask application
    app = create_app()
    
    # Initialize WebSocket
    try:
        from app.extensions import socketio
        socketio.init_app(app, async_mode='eventlet', logger=True, engineio_logger=True)
        logger.info("SocketIO initialized with eventlet")
    except Exception as e:
        logger.error(f"Failed to initialize SocketIO: {e}")
        sys.exit(1)

    # Try to initialize Telegram
    telegram_app = setup_telegram()
    
    try:
        # Run with SocketIO's eventlet server
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting server on port {port}")
        # When using eventlet, avoid the Flask reloader (it spawns multiple processes)
        socketio.run(
            app,
            host="0.0.0.0",
            port=port,
            debug=False,
            use_reloader=False,
            log_output=True
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        sys.exit(1)
