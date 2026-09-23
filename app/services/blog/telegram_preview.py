"""
Превью обложки для постов, у которых в raw_feed только ссылка t.me/.../id.

Сайт не может показать HTML-страницу Telegram как <img>. Публичные посты
отдают og:image на CDN Telegram — берём его лениво (браузер грузит картинку,
список /blog не блокируется сетевыми запросами к t.me).
"""
from __future__ import annotations

import re
import time
from typing import Dict, Tuple
from urllib.parse import parse_qs, quote, urlparse, urlunparse

import requests

_TELEGRAM_POST_HOSTS = {"t.me", "www.t.me", "telegram.me", "www.telegram.me"}
_PREVIEW_IMAGE_HOST_SUFFIXES = (
    "telegram-cdn.org",
    "cdn.telegram.org",
    "telesco.pe",
    "telegram.org",
)
_RE_USERNAME_POST = re.compile(r"^/([A-Za-z][A-Za-z0-9_]{3,})/(\d+)/?$")
_RE_PRIVATE_POST = re.compile(r"^/c/(\d+)/(\d+)/?$")
_RE_OG_IMAGE = re.compile(
    r'<meta[^>]+(?:property|name)=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.IGNORECASE,
)
_RE_OG_IMAGE_SWAP = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image["\']',
    re.IGNORECASE,
)
_RE_CDN_IMAGE = re.compile(
    r'https://cdn\d*\.(?:telegram-cdn\.org|telesco\.pe)/file/[A-Za-z0-9_\-.=?&]+(?:\.(?:jpg|jpeg|png|webp))?',
    re.IGNORECASE,
)

# post_url -> (ts, og_image_or_empty)
_og_cache: Dict[str, Tuple[float, str]] = {}
_OG_CACHE_TTL_OK_SEC = 6 * 60 * 60
_OG_CACHE_TTL_EMPTY_SEC = 5 * 60

PREVIEW_PATH = "/blog/media/telegram-preview"

_BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def is_public_telegram_post_url(value: object) -> bool:
    """Только публичный https://t.me/<channel>/<id> (без userinfo, без произвольных хостов)."""
    try:
        p = urlparse(str(value or "").strip())
    except Exception:
        return False
    if (p.scheme or "").lower() != "https":
        return False
    if p.username or p.password:
        return False
    host = (p.netloc or "").lower()
    if host not in _TELEGRAM_POST_HOSTS:
        return False
    path = p.path or ""
    return bool(_RE_USERNAME_POST.match(path) or _RE_PRIVATE_POST.match(path))


def canonical_telegram_post_url(value: object) -> str:
    raw = str(value or "").strip()
    if not is_public_telegram_post_url(raw):
        return ""
    p = urlparse(raw)
    path = (p.path or "").rstrip("/")
    host = "t.me" if "telegram.me" in (p.netloc or "").lower() else (p.netloc or "t.me").lower()
    if host.startswith("www."):
        host = host[4:]
    return urlunparse(("https", host, path, "", "", ""))


def telegram_preview_img_src(post_url: object) -> str:
    """Относительный src для <img>: браузер сам запросит og:image."""
    canonical = canonical_telegram_post_url(post_url)
    if not canonical:
        return ""
    return f"{PREVIEW_PATH}?u={quote(canonical, safe='')}"


def _is_allowed_preview_image_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if (p.scheme or "").lower() != "https":
        return False
    if p.username or p.password:
        return False
    host = (p.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (p.path or "").lower()
    if path.endswith(".mp4") or ".mp4?" in path:
        return False
    return any(host == suffix or host.endswith("." + suffix) for suffix in _PREVIEW_IMAGE_HOST_SUFFIXES)


def _parse_og_image(html: str) -> str:
    for pattern in (_RE_OG_IMAGE, _RE_OG_IMAGE_SWAP):
        m = pattern.search(html or "")
        if not m:
            continue
        candidate = (m.group(1) or "").strip()
        if candidate.startswith("//"):
            candidate = "https:" + candidate
        if _is_allowed_preview_image_url(candidate):
            return candidate
    return ""


def _parse_cdn_image_fallback(html: str) -> str:
    """Если meta og:image нет (embed), берём первый jpg/png с CDN Telegram."""
    for match in _RE_CDN_IMAGE.finditer(html or ""):
        candidate = match.group(0)
        lower = candidate.lower()
        if ".mp4" in lower:
            continue
        if _is_allowed_preview_image_url(candidate):
            return candidate
    return ""


def _fetch_html(url: str, *, timeout: float) -> str:
    # requests надёжнее urllib под gunicorn+eventlet (monkey-patched sockets).
    resp = requests.get(
        url,
        headers={
            "User-Agent": _BROWSER_UA,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        },
        timeout=timeout,
        allow_redirects=True,
    )
    resp.raise_for_status()
    final_host = (urlparse(resp.url).netloc or "").lower()
    if final_host.startswith("www."):
        final_host = final_host[4:]
    if final_host not in _TELEGRAM_POST_HOSTS and not final_host.endswith("telegram.org"):
        return ""
    return (resp.text or "")[:250_000]


def fetch_telegram_og_image(post_url: str, *, timeout: float = 8.0) -> str:
    """
    Скачивает HTML публичного t.me-поста и возвращает og:image на CDN Telegram.
    Успех кэшируется надолго; пустой ответ — коротко, чтобы ретраи сработали после сетевых сбоев.
    """
    canonical = canonical_telegram_post_url(post_url)
    if not canonical:
        return ""
    now = time.time()
    cached = _og_cache.get(canonical)
    if cached:
        age = now - cached[0]
        ttl = _OG_CACHE_TTL_OK_SEC if cached[1] else _OG_CACHE_TTL_EMPTY_SEC
        if age < ttl:
            return cached[1]

    image = ""
    try:
        html = _fetch_html(canonical, timeout=timeout)
        image = _parse_og_image(html) or _parse_cdn_image_fallback(html)
        if not image:
            # embed-страница часто содержит прямые jpg без og:image
            html_embed = _fetch_html(f"{canonical}?embed=1", timeout=timeout)
            image = _parse_og_image(html_embed) or _parse_cdn_image_fallback(html_embed)
    except Exception:
        image = ""

    _og_cache[canonical] = (now, image)
    return image


def clear_telegram_og_cache() -> None:
    """Сброс in-process кэша (после рестарта воркера и так пусто)."""
    _og_cache.clear()


def post_url_from_preview_request(query_u: object) -> str:
    """Достаёт и проверяет ?u= из запроса превью."""
    raw = str(query_u or "").strip()
    if not raw:
        return ""
    return canonical_telegram_post_url(raw)


def parse_preview_query_url(full_query: str) -> str:
    """Для тестов: u из querystring."""
    qs = parse_qs(full_query.lstrip("?"), keep_blank_values=False)
    values = qs.get("u") or []
    return post_url_from_preview_request(values[0] if values else "")
