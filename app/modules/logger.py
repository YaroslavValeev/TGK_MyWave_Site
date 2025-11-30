import logging
from logging.handlers import TimedRotatingFileHandler
import os

# Helper: on Windows convert long Unicode paths to short 8.3 paths to
# avoid potential filesystem encoding/permission issues when some
# Python runtimes or libraries mis-handle non-ASCII characters in
# filenames. This is a safe, platform-specific fallback used only for
# the log file path.
def _shortpath(path: str) -> str:
    if os.name == 'nt':
        try:
            import ctypes

            GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
            abs_path = os.path.abspath(path)
            buf = ctypes.create_unicode_buffer(260)
            res = GetShortPathNameW(abs_path, buf, len(buf))
            if res:
                return buf.value
        except Exception:
            # If anything goes wrong, fall back to the original path
            pass
    return path

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Создаём директорию logs, если нет
        if not os.path.exists('logs'):
            os.makedirs('logs')

        handler = TimedRotatingFileHandler(
            filename=_shortpath('logs/app.log'),
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
