from __future__ import annotations

from typing import Any, Dict
import json
import logging
import re
from datetime import datetime, timezone

from flask import current_app

from app.services.google_sheets_service import append_record, read_records as _read_records

logger = logging.getLogger(__name__)


_PHONE_RE = re.compile(r"(\+7|8)\d{10}")


def _sanitize_meta(meta: Any) -> str:
    """
    Convert meta to a compact JSON string without leaking PII.
    - Removes phone-like patterns
    - Truncates long values
    """
    try:
        if meta is None:
            return ""
        if not isinstance(meta, (dict, list, str, int, float, bool)):
            meta = str(meta)

        if isinstance(meta, str):
            s = _PHONE_RE.sub("***", meta)
            return s[:500]

        # dict/list -> json
        raw = json.dumps(meta, ensure_ascii=False, separators=(",", ":"))
        raw = _PHONE_RE.sub("***", raw)
        return raw[:800]
    except Exception:
        return ""


def log_analytics_event(event: Dict[str, Any]) -> None:
    """
    Append a single analytics event to the analytics sheet.
    Uses:
      - ANALYTICS_SHEET_SPREADSHEET_ID
      - ANALYTICS_SHEET_NAME

    Safe-by-default: does not store raw message bodies / phones.
    """
    if not current_app.config.get("ENABLE_ANALYTICS", True):
        return

    sheet_id = current_app.config.get("ANALYTICS_SHEET_SPREADSHEET_ID") or ""
    sheet_name = current_app.config.get("ANALYTICS_SHEET_NAME") or "analytics_statistics"
    if not sheet_id:
        return

    try:
        ts = datetime.now(timezone.utc).isoformat()
        values = [
            ts,
            str(event.get("event") or ""),
            str(event.get("context") or ""),
            str(event.get("type") or ""),
            str(event.get("user_key") or ""),
            str(event.get("ip") or ""),
            str(event.get("user_agent") or "")[:250],
            _sanitize_meta(event.get("meta")),
        ]
        append_record(sheet_id, sheet_name, values)
    except Exception as e:
        logger.debug("[analytics] failed to append event: %s", e)


def read_records(spreadsheet_id: str, worksheet_name: str) -> list[dict]:
    """Thin wrapper for sponsor analytics skeleton."""
    return _read_records(spreadsheet_id, worksheet_name) or []


