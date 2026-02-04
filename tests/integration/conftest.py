"""
Global integration test configuration.

This module ensures:
1. Google services are disabled for deterministic test runs.
2. Sheet/calendar helpers are stubbed to avoid external writes.
3. Logging is configured safely for Windows environments.
4. CSRF checks are bypassed in test client.
"""

import os
import sys
import logging
from io import StringIO

import pytest


# Disable Google services for all integration tests to avoid real API calls
# Tests will mock specific functions as needed
os.environ.setdefault('ENABLE_GOOGLE_SERVICES', '0')

# Aggressive early stub for app.services.google_sheets_service to avoid
# any real Google API calls during import-time initialization.
try:
    import types
    if 'app.services.google_sheets_service' not in sys.modules:
        gs_mod = types.ModuleType('app.services.google_sheets_service')
        # define commonly used functions returning safe defaults
        def _gs_noop(*a, **k):
            return []

        def _gs_append(*a, **k):
            return True

        gs_mod.append_record = _gs_append
        gs_mod.update_record = _gs_append
        gs_mod.append_dict_to_sheet = _gs_append
        gs_mod.update_sheet_row = _gs_append
        gs_mod.get_google_sheet = _gs_noop
        gs_mod.read_range = _gs_noop
        gs_mod.read_sheet = _gs_noop
        gs_mod.get_sheets_service = lambda *a, **k: None
        gs_mod.get_spreadsheet_metadata = lambda *a, **k: {}
        sys.modules['app.services.google_sheets_service'] = gs_mod
except Exception:
    pass


@pytest.fixture(scope='session', autouse=True)
def disable_google_services():
    """Disable Google services initialization for all integration tests."""
    os.environ['ENABLE_GOOGLE_SERVICES'] = '0'
    yield


@pytest.fixture(scope='session', autouse=True)
def configure_logging_for_tests():
    """
    Configure logging to avoid Windows PermissionError on log file rotation.
    Redirects root logger to StringIO (in-memory) for test runs.
    """
    # Get the root logger
    root_logger = logging.getLogger()
    
    # Remove file handlers that might cause rotation issues on Windows
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            root_logger.removeHandler(handler)
    
    # Add a safe in-memory handler (or NullHandler for silence)
    stream_handler = logging.StreamHandler(StringIO())
    stream_handler.setLevel(logging.WARNING)  # Only log warnings and above to reduce noise
    root_logger.addHandler(stream_handler)
    
    yield
    
    # Cleanup
    root_logger.removeHandler(stream_handler)


def _mock_append_dict_to_sheet(sheet_name, data_dict):
    """Mock sheet append."""
    return True


def _mock_update_sheet_row(sheet_name, row_index, *args, **kwargs):
    """Mock sheet update - flexible signature."""
    return True


def _mock_get_google_sheet(sheet_name):
    """Mock sheet get."""
    return []


def _mock_create_workout_if_not_exists(date_str, time_str, showcase_id=None, slot_type=None, service_type=None):
    """Mock workout creation."""
    return f"mock_workout_{date_str}_{time_str}".replace('-', '_').replace(':', '_')


def _mock_create_calendar_event(event_data):
    """Mock calendar event."""
    return True


def _mock_check_csrf():
    """Mock CSRF check - always pass."""
    return True


@pytest.fixture(autouse=True)
def stub_google_helpers(monkeypatch):
    """
    Stub Google Sheets and Calendar helpers to prevent external writes/calls.
    This fixture is automatically applied to all tests.
    """
    # Patch sheets_access module directly
    monkeypatch.setattr('app.modules.sheets_access.append_dict_to_sheet', _mock_append_dict_to_sheet)
    monkeypatch.setattr('app.modules.sheets_access.update_sheet_row', _mock_update_sheet_row)
    monkeypatch.setattr('app.modules.sheets_access.get_google_sheet', _mock_get_google_sheet)
    
    # Patch google_sheets_service
    # Patch a broad set of functions on google_sheets_service to prevent real API calls
    gs = 'app.services.google_sheets_service'
    for fn_name in (
        'append_record', 'update_record', 'append_dict_to_sheet', 'update_sheet_row',
        'get_google_sheet', 'read_range', 'read_sheet', 'get_sheets_service',
        'get_spreadsheet_metadata', 'read_range_values', 'find_or_create_sheet', 'append_row',
    ):
        try:
            monkeypatch.setattr(f'{gs}.{fn_name}', globals().get(f'_mock_{fn_name}', lambda *a, **k: []) )
        except Exception:
            # Fallback: attach a generic stub
            try:
                monkeypatch.setattr(f'{gs}.{fn_name}', lambda *a, **k: [] )
            except Exception:
                pass
    
    # Patch calendar_integration
    monkeypatch.setattr('app.modules.calendar_integration.create_workout_if_not_exists', _mock_create_workout_if_not_exists)
    # Make calendar_integration.create_calendar_event delegate to services.calendar_service
    def _calendar_call_through(*a, **k):
        try:
            import app.services as services_pkg
            svc = getattr(services_pkg, 'calendar_service', None)
            if svc and hasattr(svc, 'create_calendar_event'):
                return svc.create_calendar_event(*a, **k)
        except Exception:
            pass
        return _mock_create_calendar_event(*a, **k)

    monkeypatch.setattr('app.modules.calendar_integration.create_calendar_event', _calendar_call_through)
    # also patch alternate names used elsewhere
    try:
        monkeypatch.setattr('app.modules.calendar_integration.create_event', _mock_create_calendar_event)
    except Exception:
        pass
    try:
        monkeypatch.setattr('app.modules.calendar_integration.get_google_calendar_service', lambda *a, **k: None)
    except Exception:
        pass
    
    # Patch google_calendar_service.create_event (the actual function called by booking_service)
    def _mock_google_calendar_create_event(date, time, duration_minutes=60):
        """Mock Google Calendar event creation."""
        return {
            'id': f'mock-event-{date}-{time}',
            'status': 'confirmed',
            'summary': 'Wakesurfing Session'
        }
    
    try:
        monkeypatch.setattr('app.services.google_calendar_service.create_event', _mock_google_calendar_create_event)
    except Exception:
        pass
    
    # Patch app.services.google functions that may be called directly
    def _mock_add_event_to_calendar(service, date, time, client_name, client_phone):
        """Mock adding event to Google Calendar."""
        return True
    
    try:
        monkeypatch.setattr('app.services.google.add_event_to_calendar', _mock_add_event_to_calendar)
    except Exception:
        pass
    
    try:
        monkeypatch.setattr('app.services.google.get_google_services', lambda: (None, None, None))
    except Exception:
        pass
    
    # Patch CSRF service
    monkeypatch.setattr('app.services.csrf.check_csrf', _mock_check_csrf)
    
    # Ensure common service submodules exist as attributes on app.services
    try:
        import importlib
        import app.services as services_pkg
        for name in ('payment_service', 'email_service', 'sms_service', 'calendar_service'):
            try:
                mod = importlib.import_module(f'app.services.{name}')
            except Exception:
                # create a lightweight namespace when module file is absent
                import types
                mod = types.SimpleNamespace()
            # attach the module (or namespace) to package so tests and patches can find it
            setattr(services_pkg, name, mod)

        # Provide minimal default callables to avoid AttributeError when tests patch them
        if not hasattr(services_pkg.payment_service, 'process_payment'):
            setattr(services_pkg.payment_service, 'process_payment', lambda *a, **k: {'status': 'ok'})
        if not hasattr(services_pkg.email_service, 'send_email'):
            setattr(services_pkg.email_service, 'send_email', lambda *a, **k: True)
        if not hasattr(services_pkg.sms_service, 'send_sms'):
            setattr(services_pkg.sms_service, 'send_sms', lambda *a, **k: True)
        # calendar service: create both names commonly used in code
        if not hasattr(services_pkg.calendar_service, 'create_event'):
            setattr(services_pkg.calendar_service, 'create_event', lambda *a, **k: True)
        if not hasattr(services_pkg.calendar_service, 'create_calendar_event'):
            setattr(services_pkg.calendar_service, 'create_calendar_event', lambda *a, **k: True)
    except Exception:
        # Be conservative in tests: if registering fails, continue — other mocks still help
        pass

    yield


@pytest.fixture
def auth_headers():
    """Provide default auth headers used by many integration tests."""
    return {
        'Authorization': 'Bearer None',
        'Content-Type': 'application/json'
    }


@pytest.fixture
def booking_factory(client, auth_headers):
    """Factory to create bookings via the API (avoids direct model instantiation).

    Usage:
        booking = booking_factory({'start_date': ..., 'end_date': ..., ...})
    Returns parsed JSON booking response.
    """
    import json

    def _create(payload=None, headers=None):
        payload = payload or {
            'start_date': (None),
            'end_date': (None),
            'num_participants': 1
        }
        # If caller passes datetime values, the JSON encoder in requests will fail,
        # tests should pass ISO strings; keep minimal here.
        hdrs = headers or auth_headers
        response = client.post('/api/bookings', data=json.dumps(payload), headers=hdrs)
        try:
            return response.status_code, json.loads(response.data or b'{}')
        except Exception:
            return response.status_code, {}

    return _create


@pytest.fixture
def app():
    """Create and configure a test Flask app."""
    from app import create_app
    
    app = create_app(config_name='testing')
    
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a CLI test runner for the app."""
    return app.test_cli_runner()
