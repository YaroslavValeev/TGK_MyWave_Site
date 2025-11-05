"""Production WSGI server configuration with New Relic monitoring."""
import os
import sys
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize New Relic if configuration exists
try:
    import newrelic.agent
    if os.path.exists('newrelic.ini'):
        newrelic.agent.initialize('newrelic.ini')
        logger.info("New Relic monitoring initialized")
    else:
        logger.warning("newrelic.ini not found - skipping New Relic integration")
except ImportError:
    logger.warning("New Relic agent not installed - monitoring disabled")

# Ensure prometheus_multiproc directory exists
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

# Initialize Flask application
try:
    from app import create_app
    application = create_app()

    # Initialize SocketIO
    from app.extensions import socketio
    socketio.init_app(
        application,
        async_mode='eventlet',
        message_queue='redis://',
        path='/socket.io',
        logger=True,
        engineio_logger=True
    )
    logger.info("SocketIO initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize application: {e}")
    sys.exit(1)

# Initialize Telegram bot if possible
try:
    from telegram.ext import ApplicationBuilder
    from config import Config
    
    if Config.TELEGRAM_BOT_TOKEN:
        telegram_app = ApplicationBuilder().token(Config.TELEGRAM_BOT_TOKEN).build()
        logger.info("Telegram bot initialized successfully")
    else:
        logger.warning("TELEGRAM_BOT_TOKEN not set - skipping Telegram integration")
except Exception as e:
    logger.warning(f"Failed to initialize Telegram bot (httpx version issue?): {e}")

# For gunicorn integration
def create_app():
    """Create WSGI application for gunicorn."""
    return application