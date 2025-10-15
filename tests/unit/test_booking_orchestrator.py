import pytest
from app.services.booking_orchestrator import process_booking


def test_process_booking_happy_path(monkeypatch):
    # force slot available
    monkeypatch.setattr('app.modules.booking_utils.is_slot_available', lambda d, t: (True, ''))
    monkeypatch.setattr('app.services.crm.create_lead', lambda data: {'id': 'x'})
    monkeypatch.setattr('app.services.sheets_writer.save_client_workout_to_sheets', lambda **k: None)
    monkeypatch.setattr('app.services.sheets_writer.save_sales_deal_to_sheets', lambda **k: None)
    monkeypatch.setattr('app.modules.calendar_integration.create_calendar_event', lambda d: None)

    success, msg = process_booking({
        'name': 'Ivan',
        'phone': '+70000000000',
        'date': '2025-10-20',
        'time': '10:00'
    })
    assert success is True
    assert 'Booking' in msg or 'created' in msg


def test_process_booking_slot_unavailable(monkeypatch):
    monkeypatch.setattr('app.modules.booking_utils.is_slot_available', lambda d, t: (False, 'Нет свободных мест'))
    success, msg = process_booking({
        'name': 'Ivan',
        'phone': '+70000000000',
        'date': '2025-10-20',
        'time': '10:00'
    })
    assert success is False
    assert 'Нет свободных мест' in msg
