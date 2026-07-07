"""
MyWave Online Coaching — Telegram video ingest (Phase 2).

Clients send video to the notification bot with caption `oc_req_...`.
"""

from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Mapping, Optional

import requests
from flask import current_app, has_app_context

from app.modules.logger import get_logger
from app.services.online_coaching_store import append_request_media

logger = get_logger(__name__)

_REQUEST_ID_RE = re.compile(r"(oc_req_[0-9a-f]{12,32})", re.IGNORECASE)
_TELEGRAM_FILE_ID_KEYS = ("video", "document", "video_note")


def _cfg(key: str, default: str = "") -> str:
    if has_app_context():
        val = current_app.config.get(key)
        if val not in (None, ""):
            return str(val)
    return str(os.getenv(key, default) or "")


def _bot_token() -> str:
    return _cfg("NOTIFICATION_BOT_TOKEN") or _cfg("TELEGRAM_BOT_TOKEN")


def extract_request_id_from_text(text: str) -> str:
    match = _REQUEST_ID_RE.search(str(text or ""))
    return match.group(1).lower() if match else ""


def _file_id_from_message(message: Mapping[str, Any]) -> str:
    for key in _TELEGRAM_FILE_ID_KEYS:
        block = message.get(key)
        if isinstance(block, dict) and block.get("file_id"):
            return str(block["file_id"])
    return ""


def resolve_telegram_file_url(file_id: str, *, bot_token: str = "", timeout: int = 20) -> str:
    token = bot_token or _bot_token()
    if not token or not file_id:
        return ""
    api = f"https://api.telegram.org/bot{token}/getFile"
    response = requests.get(api, params={"file_id": file_id}, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    if not body.get("ok"):
        return ""
    file_path = str((body.get("result") or {}).get("file_path") or "").strip()
    if not file_path:
        return ""
    return f"https://api.telegram.org/file/bot{token}/{file_path}"


def extract_video_urls_from_update(update: Mapping[str, Any]) -> List[str]:
    message = update.get("message") or update.get("edited_message") or {}
    if not isinstance(message, dict):
        return []
    file_id = _file_id_from_message(message)
    if not file_id:
        return []
    url = resolve_telegram_file_url(file_id)
    return [url] if url else []


def _default_media_fields(caption: str) -> Dict[str, str]:
    lines = [line.strip() for line in str(caption or "").splitlines() if line.strip()]
    review_task = ""
    training_comment = ""
    for line in lines:
        lower = line.lower()
        if _REQUEST_ID_RE.search(line):
            continue
        if not review_task:
            review_task = line[:1000]
        elif not training_comment:
            training_comment = line[:1000]
    return {
        "review_task": review_task or "Видео загружено через Telegram",
        "training_comment": training_comment or "Комментарий не указан",
    }


def ingest_telegram_update(
    update: Mapping[str, Any],
    *,
    sheet_append=None,
    sheet_records=None,
    sheet_update=None,
) -> Dict[str, Any]:
    """Parse Telegram update and attach video to Online Coaching request."""
    message = update.get("message") or update.get("edited_message") or {}
    if not isinstance(message, dict):
        raise ValueError("no_message")

    caption = str(message.get("caption") or message.get("text") or "")
    online_request_id = extract_request_id_from_text(caption)
    if not online_request_id:
        raise ValueError("request_id_missing_in_caption")

    video_urls = extract_video_urls_from_update(update)
    if not video_urls:
        raise ValueError("no_video_in_message")

    media_payload = {
        "video_urls": video_urls,
        **_default_media_fields(caption),
    }
    updated = append_request_media(
        online_request_id,
        media_payload,
        sheet_append=sheet_append,
        sheet_records=sheet_records,
        sheet_update=sheet_update,
    )
    logger.info(
        "online_coaching_telegram_video_ingested",
        extra={"online_request_id": online_request_id, "video_count": len(video_urls)},
    )
    return {"online_request_id": online_request_id, "video_urls": video_urls, "record": updated}


def verify_telegram_webhook_secret(headers: Mapping[str, str], expected: str = "") -> bool:
    secret = expected or _cfg("TELEGRAM_WEBHOOK_SECRET") or _cfg("ONLINE_COACHING_TELEGRAM_WEBHOOK_SECRET")
    if not secret:
        return True
    received = headers.get("X-Telegram-Bot-Api-Secret-Token") or headers.get("x-telegram-bot-api-secret-token") or ""
    return received == secret
