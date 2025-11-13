import threading

import pytest


def test_global_exception_handler_triggers_sentry_and_alerts(monkeypatch, app, client):
    # Track calls
    sentry_called = {'ok': False}
    alert_called = {'ok': False}

    # Fake sentry_sdk.capture_exception by inserting a fake module into sys.modules
    import sys
    import types

    fake_mod = types.ModuleType('sentry_sdk')

    def _capture_exception(e):
        sentry_called['ok'] = True

    fake_mod.capture_exception = _capture_exception
    monkeypatch.setitem(sys.modules, 'sentry_sdk', fake_mod)

    # Replace monitoring.send_monitoring_alert to mark call
    def fake_send(msg):
        alert_called['ok'] = True
        return True

    monkeypatch.setattr('app.services.monitoring.send_monitoring_alert', fake_send)

    # Make threading.Thread start the target synchronously for test determinism
    class FakeThread:
        def __init__(self, target=None, daemon=None):
            self._target = target

        def start(self):
            if callable(self._target):
                self._target()

    monkeypatch.setattr('threading.Thread', FakeThread)

    # Register a temporary route that raises an unhandled exception
    @app.route('/__explode__')
    def explode():
        raise RuntimeError('boom')

    # Call endpoint
    resp = client.get('/__explode__')
    assert resp.status_code == 500

    # Ensure sentry and alert were invoked
    assert sentry_called['ok'] is True
    assert alert_called['ok'] is True
