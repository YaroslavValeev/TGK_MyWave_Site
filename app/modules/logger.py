from __future__ import annotations

import logging
import os
import sys
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


def _resolve_log_file() -> str:
    custom = (os.getenv("APP_LOG_FILE") or os.getenv("LOG_FILE") or "").strip()
    if custom:
        return _shortpath(custom)
    return _shortpath(os.path.join("logs", "app.log"))


def _create_file_handler(log_file: str, fmt: logging.Formatter) -> logging.Handler | None:
    """File handler; None if path is not writable (do not crash Gunicorn worker)."""
    log_dir = os.path.dirname(os.path.abspath(log_file))
    try:
        if log_dir and not os.path.isdir(log_dir):
            os.makedirs(log_dir, exist_ok=True)
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
        return fh
    except (OSError, PermissionError) as exc:
        sys.stderr.write(
            f"[logger] file handler skipped for {log_file}: {type(exc).__name__}: {exc}\n"
        )
        return None


def _configure_root_logging_once() -> None:
    global _root_logging_configured
    if _root_logging_configured:
        return
    _root_logging_configured = True

    log_file = _resolve_log_file()
    fmt = logging.Formatter("[%(asctime)s] %(levelname)s in %(module)s: %(message)s")

    root = logging.getLogger()
    if root.level == logging.NOTSET:
        root.setLevel(logging.INFO)

    fh = _create_file_handler(log_file, fmt)
    if fh is not None:
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
