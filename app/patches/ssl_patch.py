import ssl
import logging
from functools import wraps
from flask import current_app

logger = logging.getLogger(__name__)


def patch_ssl():
    """Патч для исправления проблем с SSL при подключении к Google API"""
    try:
        # Создаем новый контекст SSL с более надежными настройками
        ssl_context = ssl.create_default_context()
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.check_hostname = True

        # Устанавливаем минимальную версию TLS
        ssl_context.minimum_version = ssl.TLSVersion.TLSv1_2

        # Применяем патч
        ssl._create_default_https_context = lambda: ssl_context

        logger.info("SSL patch applied successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to apply SSL patch: {e}")
        return False


def with_ssl_retry(max_retries=3):
    """Декоратор для повторных попыток при SSL ошибках"""

    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            last_error = None

            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                except ssl.SSLError as e:
                    last_error = e
                    retries += 1
                    logger.warning(
                        f"SSL error occurred (attempt {retries}/{max_retries}): {e}"
                    )
                    if retries == max_retries:
                        break

            # Если все попытки не удались
            logger.error(f"Failed after {max_retries} attempts: {last_error}")
            raise last_error

        return wrapper

    return decorator
