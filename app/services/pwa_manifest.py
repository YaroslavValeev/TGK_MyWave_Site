"""PWA manifest builder (Club Box client install on home screen)."""

from __future__ import annotations

from typing import Any


def build_pwa_manifest(*, club: dict[str, Any] | None, static_icon_url: str, start_url: str = "/") -> dict[str, Any]:
    club = club or {}
    branding = club.get("branding") or {}
    club_meta = club.get("club") or {}
    name = (branding.get("brand_name") or club_meta.get("name") or "MyWave Wake").strip()
    short = name[:12] if len(name) > 12 else name
    theme = (branding.get("primary_color") or "#35C0CD").strip()
    modules = club.get("modules") or {}
    if modules.get("booking_boat"):
        # Запись идёт через модалку в секции услуг на главной (/calendar и /book форму не рендерят).
        start_url = "/#services" if start_url == "/" else start_url

    return {
        "name": name,
        "short_name": short,
        "description": f"{name} — запись, магазин, блог",
        "start_url": start_url,
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#ffffff",
        "theme_color": theme,
        "lang": club_meta.get("default_locale") or "ru",
        "icons": [
            {
                "src": static_icon_url,
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any maskable",
            },
            {
                "src": static_icon_url,
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
        ],
    }
