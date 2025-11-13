import types
from config import Config

import pytest


def make_resp(ok=True, status_code=200, text='OK'):
    r = types.SimpleNamespace()
    r.ok = ok
    r.status_code = status_code
    r.text = text
    return r


def test_send_monitoring_alert_not_configured(monkeypatch):
    # Ensure Config has no telegram settings
    monkeypatch.setattr(Config, 'TELEGRAM_BOT_TOKEN', None, raising=False)
    monkeypatch.setattr(Config, 'TELEGRAM_CHAT_ID', None, raising=False)

    from app.services.monitoring import send_monitoring_alert

    res = send_monitoring_alert("test message")
    assert res is False


def test_send_monitoring_alert_success(monkeypatch):
    # Provide dummy config and mock requests.get
    monkeypatch.setattr(Config, 'TELEGRAM_BOT_TOKEN', 'dummy-token', raising=False)
    monkeypatch.setattr(Config, 'TELEGRAM_CHAT_ID', '12345', raising=False)

    # Patch the requests.get used inside the monitoring helper
    def fake_get(url, params=None, timeout=None):
        return make_resp(ok=True)

    monkeypatch.setattr('app.services.monitoring.requests.get', fake_get)

    from app.services.monitoring import send_monitoring_alert

    assert send_monitoring_alert('hello') is True


def test_send_monitoring_alert_http_error(monkeypatch):
    monkeypatch.setattr(Config, 'TELEGRAM_BOT_TOKEN', 'dummy-token', raising=False)
    monkeypatch.setattr(Config, 'TELEGRAM_CHAT_ID', '12345', raising=False)

    def fake_get(url, params=None, timeout=None):
        return make_resp(ok=False, status_code=500, text='error')

    monkeypatch.setattr('app.services.monitoring.requests.get', fake_get)

    from app.services.monitoring import send_monitoring_alert

    # Should return False on HTTP error
    assert send_monitoring_alert('hello') is False
