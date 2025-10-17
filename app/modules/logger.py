import logging
from logging.handlers import TimedRotatingFileHandler
import errno
import os


class SafeTimedRotatingFileHandler(TimedRotatingFileHandler):
    """TimedRotatingFileHandler that ignores PermissionError on rollover (Windows file lock).

    On Windows os.rename can fail if another process/handler temporarily holds the file.
    We catch those errors during rollover to avoid crashing the application logging.
    """
    def doRollover(self):
        try:
            super().doRollover()
        except PermissionError as e:
            # Log to stderr/console instead of raising to avoid crashing the app.
            # Using print here because logger may be in inconsistent state during rollover.
            print(f"[logger] Warning: log rollover failed due to PermissionError: {e}")
        except OSError as e:
            # Some OS-level errors may surface as OSError; ignore rename-related errors too.
            if getattr(e, 'errno', None) in (errno.EACCES, errno.EPERM):
                print(f"[logger] Warning: log rollover OSError ignored: {e}")
            else:
                raise


def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # Создаём директорию logs, если нет
        if not os.path.exists('logs'):
            os.makedirs('logs')

        # Use safe handler to avoid Windows rename permission errors during rollover
        handler = SafeTimedRotatingFileHandler(
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
