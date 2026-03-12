"""
E2E test configuration.

- live_server with mocked Google services
- page fixture from pytest-playwright
"""
import os
import time
import threading

import pytest
import requests

# Disable Google services for E2E — tests must not depend on live API
os.environ['ENABLE_GOOGLE_SERVICES'] = '0'
os.environ.setdefault('PROMETHEUS_MULTIPROC_DIR', os.path.join(os.path.dirname(__file__), '..', '..', 'prometheus_multiproc'))

# page fixture provided by pytest-playwright (loaded via pytest.ini plugins)


@pytest.fixture(scope='session')
def live_server():
    """Start Flask app in background with mocked Google/Sheets/Calendar."""
    from unittest.mock import patch
    from app import create_app

    slots = [{'time': '10:00', 'available': True, 'remaining': 3}]
    mock_slots = lambda date: slots
    mock_calendar = lambda *a, **k: True
    mock_google = lambda: (None, None, None)

    # Stateful mock for booking duplicate test
    e2e_state = {'clients': [], 'bookings': []}

    def read_records(sheet_id, sheet_name):
        if sheet_name == 'Clients':
            return list(e2e_state['clients'])
        if sheet_name == 'Client_Workouts':
            return list(e2e_state['bookings'])
        if sheet_name == 'Workouts':
            return [{'workout_id': 'w1', 'date': '2026-12-20', 'time': '10:00', 'current_capacity': '0'}]
        if sheet_name == 'Schedule':
            return [{'day_of_week': 'sunday', 'time': '10:00', 'max_capacity': '3'}]
        return []

    def append_dict(sheet_name, data):
        if sheet_name == 'Clients':
            e2e_state['clients'].append(dict(data))
        elif sheet_name == 'Client_Workouts':
            e2e_state['bookings'].append(dict(data))

    def create_workout(d, t, *a, **k):
        return f"workout_{d}_{t}".replace('-', '_').replace(':', '_')

    with patch('app.routes.calendar_routes.get_available_slots', mock_slots), \
         patch('app.routes.calendar_routes.add_event_to_calendar', mock_calendar), \
         patch('app.routes.calendar_routes.get_google_services', mock_google), \
         patch('app.routes.calendar_routes.read_records', read_records), \
         patch('app.modules.sheets_access.append_dict_to_sheet', append_dict), \
         patch('app.modules.calendar_integration.create_workout_if_not_exists', create_workout), \
         patch('app.services.google_sheets_service.update_record', return_value=True), \
         patch('app.services.csrf.check_csrf', return_value=True):
        app = create_app(config_name='testing')
        app.config['SPREADSHEET_ID'] = 'e2e-test-sheet'
        port = 5012
        base = f'http://127.0.0.1:{port}'

        def run():
            app.run(host='0.0.0.0', port=port, threaded=True, use_reloader=False)

        thr = threading.Thread(target=run, daemon=True)
        thr.start()

        for _ in range(60):
            try:
                r = requests.get(base + '/', timeout=2)
                if r.status_code == 200:
                    break
            except Exception:
                pass
            time.sleep(0.5)

        yield base
