"""Online Coaching payment flow tests (mocked Sheets)."""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence, Tuple

import pytest

from app.services.online_coaching_payments import mark_paid, record_manual_payment_url
from app.services.online_coaching_schema import ONLINE_PAYMENTS_HEADERS, ONLINE_REQUESTS_HEADERS
from app.services.online_coaching_store import append_online_request


def _payload(**overrides: Any) -> Dict[str, Any]:
    base = {
        "name": "Ivan",
        "phone": "+79161234567",
        "service_type": "progress_month",
        "preferred_channel": "phone",
        "consent_personal_data": True,
        "consent_version": "2026-07-v1",
    }
    base.update(overrides)
    return base


class FakeSheetStore:
    def __init__(self) -> None:
        self.rows: Dict[str, List[List[str]]] = {}
        self.updates: List[Tuple[str, str, str, List[str]]] = []
        self.sales_deals: List[Dict[str, str]] = []
        self.subscriptions: List[Dict[str, str]] = []

    def append(self, spreadsheet_id: str, sheet_name: str, values: List[str]) -> None:
        self.rows.setdefault(sheet_name, []).append(values)

    def records(self, spreadsheet_id: str, sheet_name: str) -> Sequence[Mapping[str, Any]]:
        headers_map = {
            "Online_Requests": ONLINE_REQUESTS_HEADERS,
            "Online_Payments": ONLINE_PAYMENTS_HEADERS,
        }
        headers = headers_map.get(sheet_name, ())
        out = []
        for row in self.rows.get(sheet_name, []):
            out.append({headers[i]: row[i] if i < len(row) else "" for i in range(len(headers))})
        return out

    def update(self, spreadsheet_id: str, sheet_name: str, cell: str, values: List[str]) -> None:
        self.updates.append((spreadsheet_id, sheet_name, cell, values))


@pytest.fixture()
def fake_store(monkeypatch):
    store = FakeSheetStore()
    monkeypatch.setenv("SPREADSHEET_ID", "fake-sheet-id")
    monkeypatch.setattr(
        "app.services.booking.client_resolver.resolve_client",
        lambda phone, name: type("R", (), {"client_id": "cli_pay"})(),
    )
    monkeypatch.setattr(
        "app.services.sheets_writer.save_sales_deal_to_sheets",
        lambda **kwargs: store.sales_deals.append(kwargs),
    )
    monkeypatch.setattr(
        "app.services.sheets_writer.save_subscription_to_sheets",
        lambda **kwargs: store.subscriptions.append(kwargs),
    )
    return store


def test_record_manual_payment_url(fake_store):
    req_id = "oc_req_abc123456789abcd"
    append_online_request(
        _payload(),
        online_request_id=req_id,
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )

    result = record_manual_payment_url(
        req_id,
        "https://pay.tbank.ru/test",
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        sheet_update=fake_store.update,
    )
    assert result["payment_id"].startswith("oc_pay_")
    assert result["request"]["payment_status"] == "link_sent"
    assert result["request"]["request_status"] == "waiting_payment"
    assert len(fake_store.rows.get("Online_Payments", [])) == 1


def test_mark_paid_progress_month_creates_subscription(fake_store):
    req_id = "oc_req_abc123456789abcd"
    append_online_request(
        _payload(),
        online_request_id=req_id,
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )

    result = mark_paid(
        req_id,
        sheet_records=fake_store.records,
        sheet_append=fake_store.append,
        sheet_update=fake_store.update,
    )
    assert result["request"]["payment_status"] == "paid"
    assert result["request"]["request_status"] == "subscription_active"
    assert result["subscription_id"].startswith("sub_")
    assert len(fake_store.sales_deals) == 1
    assert len(fake_store.subscriptions) == 1
    assert len(fake_store.rows.get("Online_Payments", [])) == 1


def test_record_manual_payment_url_requires_url(fake_store):
    req_id = "oc_req_abc123456789abcd"
    append_online_request(
        _payload(service_type="video_check"),
        online_request_id=req_id,
        sheet_append=fake_store.append,
        sheet_records=fake_store.records,
        log_bot_event=False,
    )
    with pytest.raises(ValueError, match="payment_url_required"):
        record_manual_payment_url(
            req_id,
            "",
            sheet_records=fake_store.records,
            sheet_update=fake_store.update,
        )
