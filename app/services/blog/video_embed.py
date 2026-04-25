"""
Превью и безопасное встраивание видео для read-model блога.
"""
import re
from typing import Optional
from urllib.parse import parse_qs, urlparse

_RE_VID_FILE = re.compile(r"\.(mp4|webm|m4v|ogv)(?:$|[?#])", re.IGNORECASE)


def _norm_url(value: object) -> str:
    s = "" if value is None else str(value).strip()
    if not s:
        return ""
    if s.startswith("//"):
        return f"https:{s}"
    return s


def _youtube_watch_to_embed(url: str) -> str:
    u = _norm_url(url)
    if not u:
        return ""
    try:
        p = urlparse(u)
    except Exception:
        return ""
    host = (p.netloc or "").lower()
    if host in ("www.youtube.com", "youtube.com", "m.youtube.com"):
        if p.path == "/watch":
            v = (parse_qs(p.query or "").get("v") or [""])[0]
            if v and re.match(r"^[A-Za-z0-9_-]{6,}$", v):
                return f"https://www.youtube.com/embed/{v}"
        m = re.match(r"^/shorts/([A-Za-z0-9_-]+)", p.path or "")
        if m:
            return f"https://www.youtube.com/embed/{m.group(1)}"
    if host in ("youtu.be",):
        vid = (p.path or "").strip("/")
        if vid and re.match(r"^[A-Za-z0-9_-]{6,}$", vid):
            return f"https://www.youtube.com/embed/{vid}"
    return u


def _allowed_embed_host(host: str) -> bool:
    h = (host or "").lower()
    if h.startswith("www."):
        h = h[4:]
    return h in {
        "youtube.com",
        "youtube-nocookie.com",
        "player.vimeo.com",
        "vk.com",
        "vkvideo.ru",
        "rutube.ru",
        "ok.ru",
        "kinescope.io",
    } or h.endswith(".youtube.com") or h.endswith(".rutube.ru")


def is_safe_iframe_embed_url(url: str) -> bool:
    u = _norm_url(url)
    if not u or not u.lower().startswith("https://"):
        return False
    try:
        p = urlparse(u)
    except Exception:
        return False
    return _allowed_embed_host(p.netloc or "")


def _is_probably_video_file_url(url: str) -> bool:
    u = _norm_url(url).lower()
    return bool(_RE_VID_FILE.search(u))


def attach_video_display_fields(d: dict) -> None:
    """
    Добавляет в словарь поста поля для шаблона: video_iframe_src, video_direct_file_url, video_open_url.
    """
    v_raw = d.get("video_url") or ""
    e_raw = d.get("embed_url") or ""
    v = _norm_url(v_raw)
    e = _norm_url(e_raw)
    d["video_iframe_src"] = None
    d["video_direct_file_url"] = None
    d["video_open_url"] = None

    candidates_iframe: list[str] = []
    if e:
        candidates_iframe.append(e)
    if v:
        candidates_iframe.append(v)

    for c in candidates_iframe:
        if not c:
            continue
        u_try = _youtube_watch_to_embed(c) or c
        if is_safe_iframe_embed_url(u_try):
            d["video_iframe_src"] = u_try
            break

    if v and _is_probably_video_file_url(v) and not d["video_iframe_src"]:
        d["video_direct_file_url"] = v
    if v and not d["video_iframe_src"] and not d["video_direct_file_url"]:
        d["video_open_url"] = v
    if e and not d["video_iframe_src"] and not d["video_open_url"] and not d["video_direct_file_url"]:
        d["video_open_url"] = e
    return None
