"""
Product purchase request leads (PR53) — no online payment, manager follow-up.
"""
from __future__ import annotations

import os
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, List, Mapping, Optional

from flask import current_app

from app.modules.logger import get_logger

logger = get_logger(__name__)

PRODUCT_LEADS_SHEET = "Product_Leads"
PRODUCT_LEADS_HEADERS = [
    "lead_id",
    "name",
    "phone",
    "telegram",
    "email",
    "product_id",
    "product_title",
    "quantity",
    "comment",
    "page_url",
    "source",
    "status",
    "created_at",
]

_PHONE_RE = re.compile(r"\D+")


@dataclass(slots=True)
class ProductLeadResult:
    lead_id: str
    status: str
    sheet_name: str


def generate_lead_id() -> str:
    return f"prod_lead_{uuid.uuid4().hex[:16]}"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def validate_product_lead(data: Mapping[str, Any]) -> List[str]:
    errors: List[str] = []
    name = str(data.get("name") or "").strip()
    phone = str(data.get("phone") or "").strip()
    product_id = str(data.get("product_id") or "").strip()
    product_title = str(data.get("product_title") or "").strip()

    if len(name) < 2:
        errors.append("invalid:name")
    digits = _PHONE_RE.sub("", phone)
    if len(digits) < 10:
        errors.append("invalid:phone")
    if not product_id:
        errors.append("invalid:product_id")
    if not product_title:
        errors.append("invalid:product_title")

    qty_raw = data.get("quantity", 1)
    try:
        qty = int(qty_raw)
        if qty < 1 or qty > 99:
            errors.append("invalid:quantity")
    except (TypeError, ValueError):
        errors.append("invalid:quantity")

    return errors


def build_product_lead_row(lead_id: str, data: Mapping[str, Any], *, status: str = "new") -> List[str]:
    created = _utc_now_iso()
    row = {
        "lead_id": lead_id,
        "name": str(data.get("name") or "").strip(),
        "phone": str(data.get("phone") or "").strip(),
        "telegram": str(data.get("telegram") or "").strip(),
        "email": str(data.get("email") or "").strip(),
        "product_id": str(data.get("product_id") or "").strip(),
        "product_title": str(data.get("product_title") or "").strip(),
        "quantity": str(int(data.get("quantity") or 1)),
        "comment": str(data.get("comment") or "").strip()[:500],
        "page_url": str(data.get("page_url") or "").strip()[:500],
        "source": str(data.get("source") or "product").strip()[:64],
        "status": status,
        "created_at": created,
    }
    return [row[h] for h in PRODUCT_LEADS_HEADERS]


def resolve_spreadsheet_id() -> str:
    return (
        (current_app.config.get("SPREADSHEET_ID") if current_app else None)
        or os.getenv("SPREADSHEET_ID")
        or ""
    ).strip()


def save_product_lead(
    data: Mapping[str, Any],
    *,
    lead_id: Optional[str] = None,
    sheet_append: Optional[Callable[[str, str, List[str]], Any]] = None,
) -> ProductLeadResult:
    errors = validate_product_lead(data)
    if errors:
        raise ValueError(",".join(errors))

    lid = lead_id or generate_lead_id()
    values = build_product_lead_row(lid, data)
    sheet_name = (
        (current_app.config.get("PRODUCT_LEADS_SHEET_NAME") if current_app else None)
        or os.getenv("PRODUCT_LEADS_SHEET_NAME")
        or PRODUCT_LEADS_SHEET
    )
    spreadsheet_id = resolve_spreadsheet_id()

    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    elif spreadsheet_id:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)
    else:
        logger.info(
            "product_lead_saved_local_only",
            extra={"lead_id": lid, "product_id": data.get("product_id")},
        )

    logger.info(
        "product_lead_saved",
        extra={"lead_id": lid, "product_id": data.get("product_id"), "sheet_name": sheet_name},
    )
    return ProductLeadResult(lead_id=lid, status="new", sheet_name=sheet_name)
