import pytest
from unittest.mock import patch, MagicMock
import os
import builtins
from app.services import google

def test_get_google_services_success(monkeypatch):
    google.reset_google_services()
    # Мокаем os.path.isfile, service_account.Credentials, build
    monkeypatch.setattr(os.path, "isfile", lambda path: True)
    mock_creds = MagicMock()
    with patch("app.services.google.service_account.Credentials.from_service_account_file", return_value=mock_creds) as mock_creds_func:
        with patch("app.services.google.build") as mock_build:
            mock_drive = MagicMock()
            mock_sheets = MagicMock()
            mock_calendar = MagicMock()
            mock_build.side_effect = [mock_drive, mock_sheets, mock_calendar]
            # Мокаем current_app.config
            class DummyApp:
                config = {"GOOGLE_SERVICE_ACCOUNT_FILE": "dummy.json"}
            monkeypatch.setattr("app.services.google.current_app", DummyApp())
            # Первый вызов — инициализация
            drive, sheets, calendar = google.get_google_services()
            assert drive is mock_drive
            assert sheets is mock_sheets
            assert calendar is mock_calendar
            # Второй вызов — возвращается кэш
            drive2, sheets2, calendar2 = google.get_google_services()
            assert drive2 is drive
            assert sheets2 is sheets
            assert calendar2 is calendar
            assert mock_build.call_count == 3  # только один раз строится

def test_get_google_services_file_not_found(monkeypatch):
    google.reset_google_services()
    monkeypatch.setattr(os.path, "isfile", lambda path: False)
    class DummyApp:
        config = {"GOOGLE_SERVICE_ACCOUNT_FILE": "notfound.json"}
    monkeypatch.setattr("app.services.google.current_app", DummyApp())
    with pytest.raises(FileNotFoundError):
        google.get_google_services()


def test_reset_google_services_clears_cache(monkeypatch):
    google.reset_google_services()
    monkeypatch.setattr(os.path, "isfile", lambda path: True)
    mock_creds = MagicMock()
    with patch(
        "app.services.google.service_account.Credentials.from_service_account_file",
        return_value=mock_creds,
    ):
        with patch("app.services.google.build") as mock_build:
            mock_build.side_effect = [MagicMock(), MagicMock(), MagicMock()]

            class DummyApp:
                config = {"GOOGLE_SERVICE_ACCOUNT_FILE": "dummy.json", "SPREADSHEET_ID": "abc"}

            monkeypatch.setattr("app.services.google.current_app", DummyApp())
            google.get_google_services()
            assert mock_build.call_count == 3
            google.reset_google_services()
            mock_build.side_effect = [MagicMock(), MagicMock(), MagicMock()]
            google.get_google_services()
            assert mock_build.call_count == 6