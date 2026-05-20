"""Загрузка карточек «Официальные правила» для страницы чек-листа организатора."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import yaml

from app.modules.logger import get_logger

logger = get_logger(__name__)

BASE_DIR = Path(__file__).resolve().parents[2]
RULES_DIR = BASE_DIR / "static" / "docs" / "rules"
CONFIG_PATH = BASE_DIR / "configs" / "rules_downloads.yaml"


def _resolve_file(candidates: list[str]) -> str | None:
    """Первый существующий файл в static/docs/rules/."""
    for name in candidates:
        if not name:
            continue
        path = RULES_DIR / name
        if path.is_file():
            return name
    return None


def load_rules_downloads(
    url_for_static: Callable[..., str],
) -> list[dict[str, Any]]:
    """
    Возвращает список карточек с готовыми URL только для существующих файлов.
    """
    if not CONFIG_PATH.is_file():
        logger.warning("rules_downloads: config not found path=%s", CONFIG_PATH)
        return []

    try:
        with CONFIG_PATH.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception as exc:
        logger.warning("rules_downloads: failed to load config err=%s", exc)
        return []

    items: list[dict[str, Any]] = []
    for raw in data.get("rules") or []:
        if not isinstance(raw, dict):
            continue

        pdf_name = _resolve_file(
            [raw.get("pdf", ""), *list(raw.get("pdf_fallbacks") or [])]
        )
        docx_name = _resolve_file([raw.get("docx", "")])

        yaml_status = (raw.get("status") or "").strip()
        if pdf_name or docx_name:
            card_status = "ready"
        elif yaml_status in ("missing_file", "needs_editorial_review"):
            card_status = yaml_status
        else:
            card_status = "preparing"

        pdf_url = (
            url_for_static("static", filename=f"docs/rules/{pdf_name}")
            if pdf_name
            else None
        )
        docx_url = (
            url_for_static("static", filename=f"docs/rules/{docx_name}")
            if docx_name
            else None
        )

        items.append(
            {
                "id": raw.get("id", ""),
                "organization": raw.get("organization", ""),
                "org_short": raw.get("org_short") or raw.get("organization", ""),
                "title": raw.get("title", ""),
                "description": raw.get("description", ""),
                "tags": list(raw.get("tags") or []),
                "status": card_status,
                "pdf_url": pdf_url,
                "docx_url": docx_url,
                "has_download": bool(pdf_url or docx_url),
            }
        )

    return items
