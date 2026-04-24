"""Единый резолвер изображений для карточек Services/Shop/Projects.
Правило: карточка получает images[] (список URL файлов), cover=images[0], fallback=Place1Logo.png.
Источник images[] — скан папки static/images/...
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parents[2]
STATIC_ROOT = BASE_DIR / 'static'
_IMG_EXT = frozenset({'.jpg', '.jpeg', '.png', '.gif', '.webp'})
FALLBACK = 'images/Place1Logo.png'


def rotate_images_to_cover_index(images: list[str], cover_index: int = 0) -> list[str]:
    """
    Делает images[cover_index] первым (обложка карточки и старт внутренней карусели).
    cover_index — 0-based. При выходе за границы или 0 список не меняется.
    """
    if not images:
        return []
    try:
        idx = int(cover_index)
    except (TypeError, ValueError):
        idx = 0
    if idx <= 0 or idx >= len(images):
        return list(images)
    return images[idx:] + images[:idx]


def scan_folder_images(rel_folder: str) -> list[str]:
    """Сканирует папку и возвращает список относительных путей к изображениям (для static/)."""
    norm = rel_folder.replace('\\', '/').strip().rstrip('/')
    full = STATIC_ROOT / norm
    if not full.exists() or not full.is_dir():
        return []
    out = []
    for name in sorted(full.iterdir()):
        if name.suffix.lower() in _IMG_EXT:
            out.append(str(name.relative_to(STATIC_ROOT)).replace('\\', '/'))
    return out


def resolve_card_images(
    folder_or_file: str,
    *,
    fallback: str = FALLBACK,
) -> dict[str, Any]:
    """
    Возвращает {images, cover, fallback} для карточки.
    folder_or_file: путь к папке (images/Shop/Balanceboard) или файлу (images/Place1Logo.png).
    """
    norm = folder_or_file.replace('\\', '/').strip()
    full = STATIC_ROOT / norm

    # Явный файл — существует
    if full.exists() and full.is_file():
        return {
            'images': [norm],
            'cover': norm,
            'fallback': fallback,
        }

    # Папка — сканируем
    images = scan_folder_images(norm)
    # Fallback: Consalting ↔ Consulting (опечатка в имени папки)
    if not images and 'Consalting' in norm:
        alt = norm.replace('Consalting', 'Consulting')
        images = scan_folder_images(alt)
    elif not images and 'Consulting' in norm:
        alt = norm.replace('Consulting', 'Consalting')
        images = scan_folder_images(alt)
    if images:
        return {
            'images': images,
            'cover': images[0],
            'fallback': fallback,
        }

    # Пустой результат — только fallback
    fb_path = STATIC_ROOT / fallback
    effective_fb = fallback if fb_path.exists() else 'images/wake_challenge.jpg'
    return {
        'images': [effective_fb],
        'cover': effective_fb,
        'fallback': effective_fb,
    }
