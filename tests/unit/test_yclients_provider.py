"""Unit tests for YCLIENTS provider scaffold."""

from __future__ import annotations

import pytest

from app.services.booking.providers.yclients import (
    YclientsNotConfiguredError,
    get_yclients_provider,
)


def test_yclients_disabled_by_default(monkeypatch):
    monkeypatch.delenv("YCLIENTS_ENABLED", raising=False)
    provider = get_yclients_provider()
    assert provider.is_enabled() is False
    with pytest.raises(YclientsNotConfiguredError):
        provider.fetch_available_slots("2026-07-14")


def test_yclients_enabled_without_credentials(monkeypatch):
    monkeypatch.setenv("YCLIENTS_ENABLED", "1")
    monkeypatch.delenv("YCLIENTS_PARTNER_TOKEN", raising=False)
    monkeypatch.delenv("YCLIENTS_USER_TOKEN", raising=False)
    provider = get_yclients_provider()
    assert provider.is_enabled() is True
    with pytest.raises(YclientsNotConfiguredError):
        provider._require_enabled()
