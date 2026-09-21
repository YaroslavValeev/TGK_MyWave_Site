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
from urllib.request import Request, urlopen

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

# post_url -> (ts, og_image_or_empty)
_og_cache: Dict[str, Tuple[float, str]] = {}
_OG_CACHE_TTL_SEC = 6 * 60 * 60

PREVIEW_PATH = "/blog/media/telegram-preview"


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


def fetch_telegram_og_image(post_url: str, *, timeout: float = 2.5) -> str:
    """
    Скачивает HTML публичного t.me-поста и возвращает og:image на CDN Telegram.
    Результат кэшируется, в том числе пустой (чтобы не долбить t.me при ошибке).
    """
    canonical = canonical_telegram_post_url(post_url)
    if not canonical:
        return ""
    now = time.time()
    cached = _og_cache.get(canonical)
    if cached and (now - cached[0]) < _OG_CACHE_TTL_SEC:
        return cached[1]

    req = Request(
        canonical,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; MyWaveBlog/1.0; +https://mywavewake.ru/)",
            "Accept": "text/html,application/xhtml+xml",
        },
        method="GET",
    )
    image = ""
    try:
        with urlopen(req, timeout=timeout) as resp:  # nosec B310 — host allowlist выше
            final_host = (urlparse(resp.geturl()).netloc or "").lower()
            if final_host.startswith("www."):
                final_host = final_host[4:]
            if final_host not in _TELEGRAM_POST_HOSTS and not final_host.endswith("telegram.org"):
                image = ""
            else:
                raw = resp.read(180_000)
                html = raw.decode("utf-8", errors="ignore")
                image = _parse_og_image(html)
    except Exception:
        image = ""

    _og_cache[canonical] = (now, image)
    return image


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
