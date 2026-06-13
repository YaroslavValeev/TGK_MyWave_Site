import os
import sys
import pytest

# Ensure prometheus multiproc dir exists for tests to avoid startup errors
import tempfile
PROM_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'prometheus_multiproc'))
os.makedirs(PROM_DIR, exist_ok=True)
os.environ.setdefault('PROMETHEUS_MULTIPROC_DIR', PROM_DIR)

# Ensure repo root is on sys.path so tests can import the `app` package when
# pytest is executed from different working directories or under CI.
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

# All tests: disable Google services by default for reproducibility
os.environ.setdefault('ENABLE_GOOGLE_SERVICES', '0')

# Staging/prod .env may have BOOKING_PHASE2_*=1; force OFF before load_dotenv()
# so unit tests use mocks (load_dotenv does not override existing env vars).
for _phase2_flag in (
    'BOOKING_PHASE2_AVAILABILITY',
    'BOOKING_PHASE2_TRAVEL_BUFFER',
    'BOOKING_PHASE2_MULTI_SET_BOAT',
    'BOOKING_PHASE2_SUMMARY_V2',
    'BOOKING_PHASE2_GYM_LOCATION_V2',
):
    os.environ[_phase2_flag] = '0'

for _social_flag in (
    'SOCIAL_MODULE_ENABLED',
    'SOCIAL_WIDGET_ENABLED',
    'SOCIAL_APPLICATIONS_ENABLED',
    'SOCIAL_PUBLIC_STATS_ENABLED',
    'SOCIAL_ADMIN_NOTIFICATIONS_ENABLED',
):
    os.environ[_social_flag] = '0'

for _events_flag in (
    "EVENTS_CLASSIFIER_ENABLED",
    "EVENTS_API_ENABLED",
    "EVENTS_REVIEW_API_ENABLED",
    "EVENTS_PUBLIC_UI_ENABLED",
):
    os.environ[_events_flag] = "0"

from app import create_app
import unittest.mock as umock


# Эти файлы находятся в tools/ и не являются частью pytest-сюита сайта.
# Некоторые из них требуют опциональные зависимости (например, mcp) и ломают коллекцию.
collect_ignore = [
    "tools/mcp_inprocess_test.py",
    "tools/test_server_stub.py",
]


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    yield app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture
def mocker():
    """Simple replacement for pytest-mock's `mocker` when it's not installed.

    Provides a `.patch(target, **kwargs)` method that starts a patch and
    ensures it's stopped after the test ends.
    """
    started = []

    class _Mocker:
        def patch(self, target, **kwargs):
            p = umock.patch(target, **kwargs)
            started.append(p)
            return p.start()

    m = _Mocker()
    yield m
    # stop in reverse order
    for p in reversed(started):
        try:
            p.stop()
        except Exception:
            pass


@pytest.fixture(autouse=True)
def mock_external_apis(mocker):
    # patch common external integrations
    mocker.patch('app.services.google_sheets_service.append_record', return_value=True)
    mocker.patch('app.services.openai_service.ask', return_value='Тестовый ответ')