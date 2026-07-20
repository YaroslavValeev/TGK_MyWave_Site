"""Client display name for Calendar events (no PII in public slot APIs)."""

from __future__ import annotations

from typing import Any, Mapping


def build_client_display_name(data: Mapping[str, Any] | None) -> str:
    if not data:
        return "Клиент"
    first_name = str(data.get("first_name") or "").strip()
    last_name = str(data.get("last_name") or "").strip()
    full_name = " ".join(part for part in (first_name, last_name) if part)
    if full_name:
        return full_name
    return str(data.get("name") or "").strip() or "Клиент"
