"""
Загрузчик контента для страниц проектов.
Поддерживает Markdown, JSON, YAML файлы.
"""
import json
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False

try:
    import markdown as md
    MARKDOWN_AVAILABLE = True
except ImportError:
    MARKDOWN_AVAILABLE = False


def project_base_dir() -> Path:
    """
    Возвращает базовую директорию для контента проектов.
    Ожидаем запуск из корня проекта (где main.py).
    """
    # Путь относительно этого файла: app/services/project_content.py
    # Корень проекта: на 2 уровня выше
    return Path(__file__).resolve().parent.parent.parent / "content" / "projects"


def load_text(path: Path) -> str:
    """Читает текстовый файл."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_json(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Читает JSON файл."""
    if not path.exists():
        return default or {}
    try:
        return json.loads(load_text(path))
    except json.JSONDecodeError:
        return default or {}


def load_yaml(path: Path, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Читает YAML файл."""
    if not YAML_AVAILABLE:
        return default or {}
    if not path.exists():
        return default or {}
    try:
        return yaml.safe_load(load_text(path)) or {}
    except Exception:
        return default or {}


def render_markdown(markdown_text: str) -> str:
    """Конвертирует Markdown в HTML."""
    if not MARKDOWN_AVAILABLE:
        return markdown_text.replace("\n", "<br>")
    return md.markdown(markdown_text, extensions=["extra", "sane_lists"])


def load_safari_bundle() -> Dict[str, Any]:
    """
    Загружает весь контент для страницы Wake Surf Safari 2026.
    
    Returns:
        Словарь с ключами: html, meta, schema_event, menu, partner_packages, forms
    """
    base = project_base_dir() / "safari2026"
    
    # Загружаем файлы с fallback на пустые значения
    index_md = load_text(base / "index.md")
    meta = load_json(base / "meta.json", {
        "title": "Wake Surf Safari 2026",
        "description": "Экспедиционный вейксерф-тур по Волге",
        "og": {
            "type": "website",
            "title": "Wake Surf Safari 2026",
            "description": "Экспедиционный вейксерф-тур по Волге",
            "image": "",
            "url": ""
        },
        "twitter": {
            "card": "summary_large_image",
            "title": "Wake Surf Safari 2026",
            "description": "Экспедиционный вейксерф-тур по Волге",
            "image": ""
        }
    })
    schema_event = load_json(base / "schema-event.jsonld", {
        "@context": "https://schema.org",
        "@type": "SportsEvent",
        "name": "Wake Surf Safari 2026"
    })
    menu = load_json(base / "menu.json", [])
    partner_packages = load_json(base / "partner_packages.json", {
        "packages": [],
        "contact": {
            "email": "Y.Valeev@gmail.com",
            "phone": "+7 916 011 71 79"
        }
    })
    forms = load_yaml(base / "forms.yaml", {})
    
    # Конвертируем markdown в HTML
    html = render_markdown(index_md) if index_md else ""
    
    return {
        "html": html,
        "meta": meta,
        "schema_event": schema_event,
        "menu": menu,
        "partner_packages": partner_packages,
        "forms": forms,
    }

