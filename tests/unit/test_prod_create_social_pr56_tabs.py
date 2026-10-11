"""Unit tests for prod_create_social_pr56_tabs.py (no Google API)."""

from unittest.mock import MagicMock

import scripts.prod_create_social_pr56_tabs as tabs_mod


def test_ensure_tab_dry_run_missing_tab():
    sheets = MagicMock()
    rc = tabs_mod._ensure_tab(
        sheets=sheets,
        sid="sheet123",
        sheet_name="Social_Sessions",
        headers=("session_id", "application_id"),
        titles=[],
        validate_sheet_headers=lambda *_a, **_k: (True, []),
    )
    assert rc == 0
    sheets.spreadsheets.return_value.batchUpdate.assert_not_called()


def test_ensure_tab_apply_creates_tab(monkeypatch):
    monkeypatch.setattr(tabs_mod, "APPLY", True)
    sheets = MagicMock()
    rc = tabs_mod._ensure_tab(
        sheets=sheets,
        sid="sheet123",
        sheet_name="Social_Audit_Log",
        headers=("event_id", "timestamp"),
        titles=[],
        validate_sheet_headers=lambda *_a, **_k: (True, []),
    )
    assert rc == 0
    sheets.spreadsheets.return_value.batchUpdate.assert_called_once()
    sheets.spreadsheets.return_value.values.return_value.update.assert_called_once()
