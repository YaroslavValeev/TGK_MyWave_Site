import pytest
from app import create_app


@pytest.fixture(scope='session')
def app():
    app = create_app('testing')
    yield app


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_external_apis(monkeypatch):
    # Use monkeypatch to avoid requiring pytest-mock
    monkeypatch.setattr('app.services.google_sheets_service.append_record', lambda *a, **k: True)
    monkeypatch.setattr('app.services.openai_service.ask', lambda *a, **k: 'Тестовый ответ')


@pytest.fixture
def mocker(monkeypatch):
    """Lightweight `mocker`-like fixture for environments without pytest-mock.

    Provides basic `patch`, `patch_object` and `spy` helpers backed by pytest's monkeypatch.
    """

    import unittest.mock as _umock

    class _Mocker:
        def __init__(self, mp):
            self._mp = mp
            # helper object so tests can call `mocker.patch.object(...)`
            self._patch_helper = self.PatchHelper(self)

        def _do_patch(self, target, new=_umock._Sentinel, **kwargs):
            # If new not provided, create a Mock with kwargs (e.g., return_value)
            if new is _umock._Sentinel:
                m = _umock.Mock(**kwargs)
                self._mp.setattr(target, m)
                return m
            self._mp.setattr(target, new, **kwargs)
            return new

        def _do_patch_object(self, obj, attr, new=_umock._Sentinel, **kwargs):
            if new is _umock._Sentinel:
                m = _umock.Mock(**kwargs)
                self._mp.setattr(obj, attr, m)
                return m
            self._mp.setattr(obj, attr, new, **kwargs)
            return new

        class PatchHelper:
            def __init__(self, outer):
                self._outer = outer

            def __call__(self, target, new=_umock._Sentinel, **kwargs):
                return self._outer._do_patch(target, new, **kwargs)

            def object(self, obj, attr, new=_umock._Sentinel, **kwargs):
                return self._outer._do_patch_object(obj, attr, new, **kwargs)

        @property
        def patch(self):
            return self._patch_helper

        def patch_object(self, obj, attr, new=_umock._Sentinel, **kwargs):
            return self._do_patch_object(obj, attr, new, **kwargs)

        def spy(self, obj, name):
            orig = getattr(obj, name)
            calls = []

            def _spy(*a, **k):
                calls.append((a, k))
                return orig(*a, **k)

            self._mp.setattr(obj, name, _spy)
            _spy.calls = calls
            return _spy

    return _Mocker(monkeypatch)