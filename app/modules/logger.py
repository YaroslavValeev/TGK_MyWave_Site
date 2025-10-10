import logging
from logging.handlers import TimedRotatingFileHandler
import os

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Создаём директорию logs, если нет
        if not os.path.exists('logs'):
            os.makedirs('logs')

        handler = TimedRotatingFileHandler(
            filename='logs/app.log',
            when='midnight',
            interval=1,
            backupCount=7,
            encoding='utf-8'
        )
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s')
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        logger.addHandler(handler)

        # Консольный логгер для разработки
        console = logging.StreamHandler()
        console.setLevel(logging.DEBUG)
        console.setFormatter(formatter)
        logger.addHandler(console)

    return logger

def log_event(event):
    lg = get_logger(__name__)
    lg.info(f"Событие: {event}")

# Глобальный логгер для импорта
logger = get_logger(__name__)
