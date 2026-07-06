"""
MyWave Online Coaching — payment records (manual T-Bank URL MVP).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Mapping, Optional

from app.modules.logger import get_logger
from app.services.online_coaching_schema import (
    ONLINE_PAYMENTS_HEADERS,
    ONLINE_PAYMENTS_SHEET,
    SERVICE_PRICES,
    payment_timing_for_service,
)
from app.services.online_coaching_store import (
    find_request_by_id,
    resolve_sheet_name,
    resolve_spreadsheet_id,
    row_dict_to_values,
    update_request_fields,
)

logger = get_logger(__name__)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _payment_amount(service_type: str, amount: Optional[float] = None) -> float:
    if amount is not None:
        return float(amount)
    return float(SERVICE_PRICES.get(service_type, 0))


def record_manual_payment_url(
    online_request_id: str,
    url: str,
    amount: Optional[float] = None,
    *,
    sheet_append=None,
    sheet_records=None,
    sheet_update=None,
) -> Dict[str, Any]:
    payment_url = str(url or "").strip()
    if not payment_url:
        raise ValueError("payment_url_required")

    _row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if record is None:
        raise ValueError("request_not_found")

    service_type = record.get("service_type", "")
    client_id = record.get("client_id", "")
    pay_amount = _payment_amount(service_type, amount)
    payment_id = f"oc_pay_{uuid.uuid4().hex[:12]}"
    ts = _utc_now_iso()

    payment_row = {
        "payment_id": payment_id,
        "online_request_id": online_request_id,
        "client_id": client_id,
        "amount": str(int(pay_amount)),
        "currency": "RUB",
        "service_type": service_type,
        "payment_timing": payment_timing_for_service(service_type),
        "tbank_order_id": "",
        "tbank_payment_url": payment_url,
        "payment_status": "link_sent",
        "created_at": ts,
        "paid_at": "",
        "remark": "manual_tbank_url",
    }
    values = row_dict_to_values(payment_row, ONLINE_PAYMENTS_HEADERS)
    spreadsheet_id = resolve_spreadsheet_id()
    sheet_name = resolve_sheet_name("ONLINE_PAYMENTS_SHEET_NAME", ONLINE_PAYMENTS_SHEET)
    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)

    updated = update_request_fields(
        online_request_id,
        {
            "tbank_payment_url": payment_url,
            "payment_status": "link_sent",
            "request_status": "waiting_payment",
        },
        sheet_records=sheet_records,
        sheet_update=sheet_update,
    )
    logger.info(
        "online_coaching_payment_url_recorded",
        extra={"online_request_id": online_request_id, "payment_id": payment_id},
    )
    return {"payment_id": payment_id, "request": updated}


def mark_paid(
    online_request_id: str,
    *,
    amount: Optional[float] = None,
    sheet_records=None,
    sheet_append=None,
    sheet_update=None,
) -> Dict[str, Any]:
    _row_number, record = find_request_by_id(online_request_id, sheet_records=sheet_records)
    if record is None:
        raise ValueError("request_not_found")

    service_type = record.get("service_type", "")
    client_id = record.get("client_id", "")
    pay_amount = _payment_amount(service_type, amount)
    paid_at = _utc_now_iso()
    final_status = "subscription_active" if service_type == "progress_month" else "paid"

    updated = update_request_fields(
        online_request_id,
        {
            "payment_status": "paid",
            "request_status": final_status,
        },
        sheet_records=sheet_records,
        sheet_update=sheet_update,
    )

    payment_id = f"oc_pay_{uuid.uuid4().hex[:12]}"
    payment_row = {
        "payment_id": payment_id,
        "online_request_id": online_request_id,
        "client_id": client_id,
        "amount": str(int(pay_amount)),
        "currency": "RUB",
        "service_type": service_type,
        "payment_timing": payment_timing_for_service(service_type),
        "tbank_order_id": "",
        "tbank_payment_url": record.get("tbank_payment_url", ""),
        "payment_status": "paid",
        "created_at": paid_at,
        "paid_at": paid_at,
        "remark": "admin_mark_paid",
    }
    values = row_dict_to_values(payment_row, ONLINE_PAYMENTS_HEADERS)
    spreadsheet_id = resolve_spreadsheet_id()
    sheet_name = resolve_sheet_name("ONLINE_PAYMENTS_SHEET_NAME", ONLINE_PAYMENTS_SHEET)
    if sheet_append is not None:
        sheet_append(spreadsheet_id, sheet_name, values)
    else:
        from app.services.google_sheets_service import append_record

        append_record(spreadsheet_id, sheet_name, values)

    from app.services.sheets_writer import save_sales_deal_to_sheets

    save_sales_deal_to_sheets(
        deal_id=f"deal_{uuid.uuid4().hex[:12]}",
        client_id=client_id,
        amount=str(int(pay_amount)),
        deal_type=service_type,
        payment_method="tbank",
        date_closed=paid_at[:10],
        remark=f"online_request_id={online_request_id}",
    )

    subscription_id = ""
    if service_type == "progress_month" and client_id:
        from app.services.sheets_writer import save_subscription_to_sheets

        purchase_date = paid_at[:10]
        expiry = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
        subscription_id = f"sub_{uuid.uuid4().hex[:12]}"
        save_subscription_to_sheets(
            subscription_id=subscription_id,
            client_id=client_id,
            package_type="progress_month",
            total_sessions="8",
            used_sessions="0",
            purchase_date=purchase_date,
            expiry_date=expiry,
            status="active",
        )

    logger.info(
        "online_coaching_mark_paid",
        extra={
            "online_request_id": online_request_id,
            "service_type": service_type,
            "subscription_id": subscription_id or None,
        },
    )
    return {
        "online_request_id": online_request_id,
        "request": updated,
        "amount": pay_amount,
        "subscription_id": subscription_id,
        "payment_id": payment_id,
    }
