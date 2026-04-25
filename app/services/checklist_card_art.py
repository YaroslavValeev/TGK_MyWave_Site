"""
Иллюстрации карточек чек-листа организатора.

Файлы кладите в: static/images/Project/CheckList_Competion/cards/
Имя файла = id чекбокса карточки (без расширения), например: judge-1-1.jpg, aqua-2-3.png
"""
from __future__ import annotations

from typing import Dict

from flask import url_for

from app.services.images_resolver import STATIC_ROOT

_CARDS = STATIC_ROOT / "images" / "Project" / "CheckList_Competion" / "cards"
_IMG_EXT = {".jpg", ".jpeg", ".png", ".webp"}


def scan_checklist_card_illustrations() -> Dict[str, str]:
    """
    Сканирует папку cards/ и строит словарь {checkbox_id: относительный путь static}.
    У одного id берётся первый найденный файл по перечисленным расширениям.
    """
    out: Dict[str, str] = {}
    if not _CARDS.is_dir():
        return out
    for p in sorted(_CARDS.iterdir()):
        if not p.is_file():
            continue
        if p.suffix.lower() not in _IMG_EXT:
            continue
        stem = p.stem
        if not stem or stem in out:
            continue
        rel = p.relative_to(STATIC_ROOT).as_posix()
        out[stem] = rel
    return out


def checklist_art_url_map_for_js() -> Dict[str, str]:
    """
    Словарь id → абсолютный URL (для background-image в JS), только для существующих файлов.
    """
    raw = scan_checklist_card_illustrations()
    return {k: url_for("static", filename=v) for k, v in raw.items()}
