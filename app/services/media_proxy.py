"""
Отдача внешних обложек (Tour, RSS-источники блога) с нашего домена.

Браузер посетителя не всегда получает картинку с чужого сайта (хотлинк-защита,
медленный сервер, блокировки) и показывает заглушку. Сервер один раз скачивает
файл с разрешённого хоста, кладёт в кэш на диск и дальше отдаёт его сам.
"""
from __future__ import annotations

import hashlib
import logging
import os
import tempfile
from typing import Optional
from urllib.parse import quote, urlparse

import requests

logger = logging.getLogger(__name__)

PROXY_PATH = "/media/ext"

DEFAULT_ALLOWED_HOSTS = (
    "mywavetour.ru",
    "wakeboardingmag.com",
)
MAX_BYTES = 8 * 1024 * 1024
FETCH_TIMEOUT = (10, 20)

_CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
}

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def allowed_hosts() -> tuple[str, ...]:
    raw = (os.environ.get("EXTERNAL_IMAGE_PROXY_HOSTS") or "").strip()
    if not raw:
        return DEFAULT_ALLOWED_HOSTS
    return tuple(h.strip().lower() for h in raw.split(",") if h.strip())


def _normalized_host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def is_proxyable_url(url: object) -> bool:
    """Только https на разрешённый хост (или его поддомен), без логина в URL и нестандартных портов."""
    try:
        p = urlparse(str(url or "").strip())
    except Exception:
        return False
    if (p.scheme or "").lower() != "https":
        return False
    if p.username or p.password or p.port not in (None, 443):
        return False
    host = _normalized_host(p.geturl())
    if not host:
        return False
    return any(host == h or host.endswith("." + h) for h in allowed_hosts())


def proxied_image_url(url: object) -> str:
    """URL для <img src>: разрешённые внешние картинки идут через наш домен, остальное без изменений."""
    value = str(url or "").strip()
    if not value or not is_proxyable_url(value):
        return value
    return f"{PROXY_PATH}?u={quote(value, safe='')}"


def _cache_dir(static_folder: str) -> str:
    path = os.path.join(static_folder, "uploads", "ext_cache")
    os.makedirs(path, exist_ok=True)
    return path


def _cache_key(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:40]


def find_cached(url: str, static_folder: str) -> Optional[str]:
    directory = _cache_dir(static_folder)
    key = _cache_key(url)
    for ext in _CONTENT_TYPE_EXT.values():
        candidate = os.path.join(directory, key + ext)
        if os.path.isfile(candidate):
            return candidate
    return None


def fetch_and_cache(url: str, static_folder: str) -> Optional[str]:
    """Скачивает картинку в кэш. None — если не удалось (вызывающий отдаёт редирект на оригинал)."""
    if not is_proxyable_url(url):
        return None
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": _BROWSER_UA, "Accept": "image/avif,image/webp,image/*,*/*;q=0.8"},
            timeout=FETCH_TIMEOUT,
            allow_redirects=False,
            stream=True,
        )
    except requests.RequestException as exc:
        logger.info("media_proxy_fetch_failed host=%s error=%s", _normalized_host(url), type(exc).__name__)
        return None

    try:
        if resp.status_code != 200:
            logger.info("media_proxy_bad_status host=%s status=%s", _normalized_host(url), resp.status_code)
            return None
        content_type = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        ext = _CONTENT_TYPE_EXT.get(content_type)
        if not ext:
            logger.info("media_proxy_not_image host=%s type=%s", _normalized_host(url), content_type)
            return None

        directory = _cache_dir(static_folder)
        target = os.path.join(directory, _cache_key(url) + ext)
        fd, tmp_path = tempfile.mkstemp(dir=directory, suffix=".part")
        # os.fdopen под eventlet превращается в GreenPipe и ломается на обычных файлах.
        os.close(fd)
        size = 0
        try:
            with open(tmp_path, "wb") as fh:
                for chunk in resp.iter_content(64 * 1024):
                    size += len(chunk)
                    if size > MAX_BYTES:
                        raise ValueError("too_large")
                    fh.write(chunk)
            os.replace(tmp_path, target)
        except Exception as exc:
            logger.info("media_proxy_write_failed host=%s error=%s", _normalized_host(url), exc)
            try:
                os.remove(tmp_path)
            except OSError:
                pass
            return None
        return target
    finally:
        resp.close()
