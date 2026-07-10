"""Unit tests for client display name helper."""

from __future__ import annotations

from app.services.booking.client_display import build_client_display_name


def test_full_name():
    assert build_client_display_name({"first_name": "Иван", "last_name": "Иванов"}) == "Иван Иванов"


def test_name_only():
    assert build_client_display_name({"name": "Пётр"}) == "Пётр"


def test_fallback_client():
    assert build_client_display_name({}) == "Клиент"
