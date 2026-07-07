"""Camp public routes behind feature flags."""

import pytest

from app.config import camp_features


@pytest.fixture
def camp_public_enabled(monkeypatch):
    monkeypatch.setenv("CAMP_MODULE_ENABLED", "1")
    monkeypatch.setenv("CAMP_PUBLIC_ENABLED", "1")
    monkeypatch.setattr(camp_features, "is_camp_module_enabled", lambda: True)
    monkeypatch.setattr(camp_features, "is_camp_public_enabled", lambda: True)


def test_camp_index_404_when_disabled(client):
    r = client.get("/projects/camp")
    assert r.status_code == 404


def test_camp_api_404_when_disabled(client):
    r = client.get("/api/camps")
    assert r.status_code == 404
