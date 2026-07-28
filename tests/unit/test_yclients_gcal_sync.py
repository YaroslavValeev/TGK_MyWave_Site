"""Unit tests for YCLIENTS → GCal sync helpers."""

from __future__ import annotations

from datetime import datetime

from app.services.booking.yclients_sync import (
    _parse_yclients_datetime,
    normalize_webhook_record,
    parse_mw_id_from_comment,
    parse_source_from_comment,
)


def test_parse_source_and_mw_id():
    comment = "mw_source=telegram | mw_id=abc-1 | note"
    assert parse_source_from_comment(comment) == "telegram"
    assert parse_mw_id_from_comment(comment) == "abc-1"
    assert parse_source_from_comment("") == "yclients"


def test_parse_yclients_datetime_formats():
    d1 = _parse_yclients_datetime("2026-07-31 20:30:00")
    assert isinstance(d1, datetime)
    assert d1.hour == 20 and d1.minute == 30
    d2 = _parse_yclients_datetime("2026-07-31T20:30:00+03:00")
    assert d2 is not None
    assert d2.hour == 20


def test_normalize_and_selftest_skip_path(monkeypatch, app):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.setenv("YCLIENTS_GCAL_MIRROR_ENABLED", "1")
    from app.services.booking.yclients_sync import sync_record_to_calendar

    with app.app_context():
        result = sync_record_to_calendar(
            {
                "company_id": "2043174",
                "record_id": "42",
                "lifecycle": "waiting",
                "event_status": "create",
                "datetime": None,
                "raw": {"id": 42},
            }
        )
    assert result["status"] == "accepted"
    assert result["mirror"] == "skipped_selftest"


def test_normalize_webhook_envelope():
    payload = {
        "company_id": 2043174,
        "resource": "record",
        "resource_id": 187,
        "status": "create",
        "data": {
            "id": 187,
            "attendance": 0,
            "datetime": "2026-07-31T20:30:00+03:00",
            "comment": "mw_source=site | mw_id=x",
        },
    }
    n = normalize_webhook_record(payload)
    assert n["record_id"] == "187"
    assert n["lifecycle"] == "waiting"
    assert "mw_source=site" in n["comment"]
