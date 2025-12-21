"""
Рендер Markdown + санитайзер (безопасность).
"""
import re
from typing import Optional

try:
    import bleach
    from markdown import markdown
    MARKDOWN_AVAILABLE = True
    BLEACH_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False
    BLEACH_AVAILABLE = False
    from markupsafe import escape


_ALLOWED_TAGS = None
_ALLOWED_ATTRS = None
_ALLOWED_PROTOCOLS = None

if BLEACH_AVAILABLE:
    _ALLOWED_TAGS = bleach.sanitizer.ALLOWED_TAGS.union({
        "p", "br", "hr",
        "h1", "h2", "h3", "h4",
        "blockquote", "pre", "code",
        "ul", "ol", "li",
        "strong", "em",
        "a",
        "img"
    })
    _ALLOWED_ATTRS = dict(bleach.sanitizer.ALLOWED_ATTRIBUTES)
    _ALLOWED_ATTRS.update({
        "a": ["href", "title", "target", "rel"],
        "img": ["src", "alt", "title"]
    })
    _ALLOWED_PROTOCOLS = bleach.sanitizer.ALLOWED_PROTOCOLS.union({"tg"})


def safe_render_markdown(md: str) -> str:
    """
    Рендерит Markdown в безопасный HTML.
    Если библиотеки недоступны - возвращает экранированный текст.
    """
    if not md:
        return ""
    
    if MARKDOWN_AVAILABLE:
        html = markdown(md or "", extensions=["extra", "tables", "fenced_code"])
    else:
        # Fallback: простой текст с экранированием
        html = escape(md).replace("\n\n", "</p><p>").replace("\n", "<br>")
        html = f"<p>{html}</p>"
    
    if BLEACH_AVAILABLE:
        html = bleach.clean(
            html,
            tags=list(_ALLOWED_TAGS),
            attributes=_ALLOWED_ATTRS,
            protocols=list(_ALLOWED_PROTOCOLS),
            strip=True
        )
        # Безопасные ссылки
        html = re.sub(r'<a ', '<a rel="noopener noreferrer" target="_blank" ', html)
        html = bleach.linkify(html)
    else:
        # Fallback: полное экранирование
        html = escape(md).replace("\n", "<br>")
    
    return html
