"""Client find/create for web bookings."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from flask import current_app

from app.services.booking.phone import normalize_phone
from app.services.google_sheets_service import read_records

logger = logging.getLogger(__name__)


@dataclass
class ClientResolveResult:
    client_id: str
    created: bool
    matched_by: str  # phone | new


def _read_clients():
    sid = current_app.config["SPREADSHEET_ID"]
    return read_records(sid, "Clients")


def resolve_client(phone: str, name: str) -> ClientResolveResult:
    """
    Web booking: find by normalized phone or create client_<ts>.
    Never overwrite telegram_user_id on existing rows (read-only reuse).
    """
    normalized = normalize_phone(phone)
    if not normalized:
        raise ValueError("phone required")

    for client in _read_clients():
        existing_phone = normalize_phone(client.get("phone") or "")
        if existing_phone and existing_phone == normalized:
            cid = client.get("client_id") or ""
            if cid:
                logger.info(
                    "client_resolved",
                    extra={
                        "source": "web",
                        "matched_by": "phone",
                        "client_id_tail": str(cid)[-8:],
                        "client_created": False,
                    },
                )
                return ClientResolveResult(
                    client_id=cid, created=False, matched_by="phone"
                )

    new_id = f"client_{int(time.time())}"
    created_at = datetime.utcnow().isoformat()
    client_data = {
        "client_id": new_id,
        "telegram_user_id": "",
        "name": name,
        "phone": normalized,
        "email": "",
        "level": "beginner",
        "created_at": created_at,
        "source": "web",
        "status": "new",
        "ref_code": "",
        "last_active": created_at,
    }
    from app.modules.sheets_access import append_dict_to_sheet

    append_dict_to_sheet("Clients", client_data)
    logger.info(
        "client_resolved",
        extra={
            "source": "web",
            "matched_by": "new",
            "client_id_tail": str(new_id)[-8:],
            "client_created": True,
        },
    )
    return ClientResolveResult(client_id=new_id, created=True, matched_by="new")


def resolve_client_telegram(telegram_user_id: str, name: str, phone: str = "") -> ClientResolveResult:
    """Telegram path: client_id = str(telegram_user_id)."""
    tid = str(telegram_user_id).strip()
    if not tid:
        raise ValueError("telegram_user_id required")
    normalized = normalize_phone(phone) if phone else ""

    for client in _read_clients():
        if str(client.get("telegram_user_id") or "").strip() == tid:
            cid = client.get("client_id") or tid
            return ClientResolveResult(client_id=cid, created=False, matched_by="telegram_user_id")

    if normalized:
        for client in _read_clients():
            if normalize_phone(client.get("phone") or "") == normalized:
                cid = client.get("client_id") or ""
                if cid and not str(client.get("telegram_user_id") or "").strip():
                    # Reuse web client but do not write telegram here (no update API in Phase 1)
                    return ClientResolveResult(client_id=cid, created=False, matched_by="phone")

    client_data = {
        "client_id": tid,
        "telegram_user_id": tid,
        "name": name,
        "phone": normalized,
        "email": "",
        "skill_level": "",
        "source": "telegram",
        "status": "new",
        "notes": "",
        "last_active": datetime.utcnow().isoformat(),
    }
    from app.modules.sheets_access import append_dict_to_sheet

    append_dict_to_sheet("Clients", client_data)
    return ClientResolveResult(client_id=tid, created=True, matched_by="new")
