import eventlet
import socket
import dns.resolver
import logging
from functools import lru_cache
from typing import List, Tuple, Any
import time

# Настройка логгера
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Кэш для DNS-запросов с временем жизни
_dns_cache = {}
_dns_cache_times = {}
_DNS_CACHE_TTL = 300  # 5 минут


def cached_dns_resolver(host: str) -> List[str]:
    """Кэширующий декоратор для DNS-резолвинга"""
    current_time = time.time()

    # Проверяем кэш
    if host in _dns_cache:
        if current_time - _dns_cache_times[host] < _DNS_CACHE_TTL:
            return _dns_cache[host]
        else:
            # Удаляем устаревшие записи
            del _dns_cache[host]
            del _dns_cache_times[host]
    return None


def resolve_dns(host: str) -> List[str]:
    """Резолвим DNS с поддержкой IPv4 и IPv6"""
    # Используем кэширующий резолвер
    result = cached_dns_resolver(host)
    if result:
        return result

    ips = []

    # Пробуем IPv4
    try:
        answers = dns.resolver.resolve(host, "A")
        ips.extend(str(rdata) for rdata in answers)
    except Exception as e:
        logger.debug(f"IPv4 resolution failed for {host}: {e}")

    # Пробуем IPv6
    try:
        answers = dns.resolver.resolve(host, "AAAA")
        ips.extend(str(rdata) for rdata in answers)
    except Exception as e:
        logger.debug(f"IPv6 resolution failed for {host}: {e}")

    if not ips:
        raise dns.resolver.NoAnswer(f"No DNS records found for {host}")

    # Сохраняем в кэш
    _dns_cache[host] = ips
    _dns_cache_times[host] = time.time()

    return ips


# Оригинальная функция socket.getaddrinfo
_orig_getaddrinfo = socket.getaddrinfo


def _getaddrinfo(*args: Any, **kwargs: Any) -> List[Tuple]:
    """Улучшенная версия getaddrinfo с поддержкой DNS-резолвинга"""
    host, port = args[0], args[1]

    # Если это IP-адрес или localhost, используем оригинальную функцию
    if host in ("localhost", "127.0.0.1", "::1") or ":" in host:
        return _orig_getaddrinfo(*args, **kwargs)

    # Для доменов Google используем Google DNS (8.8.8.8)
    google_domains = [
        ".googleapis.com",
        ".google.com",
        "oauth2.googleapis.com",
        "sheets.googleapis.com",
    ]
    if any(domain in host for domain in google_domains):
        try:
            # Создаем новый резолвер с серверами Google
            resolver = dns.resolver.Resolver()
            resolver.nameservers = ["8.8.8.8", "8.8.4.4"]
            resolver.timeout = 3
            resolver.lifetime = 3
            answers = resolver.resolve(host, "A")
            ip = str(answers[0])
            logger.info(f"Resolved {host} to {ip} using Google DNS")
            return _orig_getaddrinfo(ip, port, *args[2:], **kwargs)
        except Exception as e:
            logger.error(
                f"Failed to resolve {host} using Google DNS ({type(e).__name__}): {e}"
            )
            # Если это временная ошибка, пытаемся использовать системный DNS
            if isinstance(
                e,
                (
                    dns.resolver.NoNameservers,
                    dns.resolver.NoAnswer,
                    dns.resolver.Timeout,
                ),
            ):
                logger.info(f"Falling back to system DNS for {host}")
                return _orig_getaddrinfo(*args, **kwargs)
            raise
        # Пытаемся использовать системный DNS как запасной вариант
        return _orig_getaddrinfo(*args, **kwargs)

    try:
        # Сначала пробуем стандартный метод
        return _orig_getaddrinfo(*args, **kwargs)
    except socket.gaierror as e:
        logger.info(
            f"Standard DNS resolution failed for {host}, trying alternative method"
        )
        try:
            # Получаем список IP-адресов
            ips = resolve_dns(host)

            # Пробуем каждый IP по очереди
            for ip in ips:
                try:
                    return _orig_getaddrinfo(ip, port, *args[2:], **kwargs)
                except socket.gaierror:
                    continue

            raise socket.gaierror(f"All resolved IPs failed for {host}")
        except Exception as e:
            logger.error(f"DNS resolution error for {host}: {str(e)}")
            from flask import current_app

            if current_app:
                current_app.logger.error(f"DNS resolution error: {str(e)}")
            raise


# Применяем патч
eventlet.monkey_patch(socket=True)
socket.getaddrinfo = _getaddrinfo

logger.info("DNS patch applied successfully")
