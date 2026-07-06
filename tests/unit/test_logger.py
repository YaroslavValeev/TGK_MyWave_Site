"""Logger bootstrap — must not crash when log file is not writable."""

from __future__ import annotations

import importlib
import logging
import sys
from unittest.mock import patch

import pytest


@pytest.fixture()
def fresh_logger_module():
    """Reload logger module to reset one-time root configuration."""
    if "app.modules.logger" in sys.modules:
        del sys.modules["app.modules.logger"]
    mod = importlib.import_module("app.modules.logger")
    mod._root_logging_configured = False
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)
    yield mod
    mod._root_logging_configured = False
    for h in list(logging.getLogger().handlers):
        logging.getLogger().removeHandler(h)


def test_get_logger_survives_unwritable_log_file(fresh_logger_module, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("LOG_USE_TIMED_ROTATION", "0")

    with patch("app.modules.logger.logging.FileHandler", side_effect=PermissionError(13, "denied")):
        logger = fresh_logger_module.get_logger("test_logger_permissions")
        logger.info("bootstrap_ok")

    root = logging.getLogger()
    assert any(isinstance(h, logging.StreamHandler) for h in root.handlers)
    assert not any(
        isinstance(h, logging.FileHandler) and not isinstance(h, logging.StreamHandler)
        for h in root.handlers
    )
