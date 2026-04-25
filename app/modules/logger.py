import logging
import os
from logging.handlers import TimedRotatingFileHandler

# Один общий файловый handler на root: иначе каждый вызов get_logger(name)
# добавлял свой TimedRotatingFileHandler на тот же logs/app.log — на Windows
# при rollover несколько дескрипторов держали файл → WinError 32.

_root_logging_configured = False


def _shortpath(path: str) -> str:
    if os.name == "nt":
        try:
            import ctypes

            GetShortPathNameW = ctypes.windll.kernel32.GetShortPathNameW
            abs_path = os.path.abspath(path)
            buf = ctypes.create_unicode_buffer(260)
            res = GetShortPathNameW(abs_path, buf, len(buf))
            if res:
                return buf.value
        except Exception:
            pass
    return path


def _use_timed_rotation() -> bool:
    """На Windows по умолчанию без rollover (FileHandler). На POSIX — суточная ротация."""
    v = (os.getenv("LOG_USE_TIMED_ROTATION") or "").strip().lower()
    if v in ("1", "true", "yes"):
        return True
    if v in ("0", "false", "no"):
        return False
    return os.name != "nt"


def _configure_root_logging_once() -> None:
    global _root_logging_configured
    if _root_logging_configured:
        return
    _root_logging_configured = True

    if not os.path.exists("logs"):
        os.makedirs("logs")

    log_file = _shortpath(os.path.join("logs", "app.log"))
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")

    root = logging.getLogger()
    if root.level == logging.NOTSET:
        root.setLevel(logging.INFO)

    if _use_timed_rotation():
        fh: logging.Handler = TimedRotatingFileHandler(
            filename=log_file,
            when="midnight",
            interval=1,
            backupCount=7,
            encoding="utf-8",
        )
    else:
        fh = logging.FileHandler(log_file, encoding="utf-8")

    fh.setLevel(logging.INFO)
    fh.setFormatter(fmt)
    root.addHandler(fh)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(fmt)
    root.addHandler(ch)


def get_logger(name):
    _configure_root_logging_once()
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    return logger


def log_event(event):
    lg = get_logger(__name__)
    lg.info("Событие: %s", event)


logger = get_logger(__name__)
