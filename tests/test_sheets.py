import pytest
from unittest.mock import MagicMock
from app.modules import sheets


def test_get_sheet_records():
    # Мокаем сервис и ответ Google Sheets API
    mock_service = MagicMock()
    mock_service.spreadsheets().values().get().execute.return_value = {
        "values": [
            ["id", "name", "phone"],
            ["1", "Иван", "+79991234567"],
            ["2", "Оля", "+79991112233"],
        ]
    }
    records, headers = sheets.get_sheet_records(mock_service, "sheet_id", "Clients")
    assert headers == ["id", "name", "phone"]
    assert records == [
        {"id": "1", "name": "Иван", "phone": "+79991234567"},
        {"id": "2", "name": "Оля", "phone": "+79991112233"},
    ]


def test_get_sheet_records_empty():
    mock_service = MagicMock()
    mock_service.spreadsheets().values().get().execute.return_value = {"values": []}
    records, headers = sheets.get_sheet_records(mock_service, "sheet_id", "Clients")
    assert records == []
    assert headers == []


def test_append_to_sheet():
    mock_service = MagicMock()
    # Проверяем, что append вызывается с нужными параметрами
    sheets.append_to_sheet(
        mock_service, "sheet_id", "Clients", [["3", "Петя", "+79990001122"]]
    )
    mock_service.spreadsheets().values().append.assert_called_once_with(
        spreadsheetId="sheet_id",
        range="Clients!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": [["3", "Петя", "+79990001122"]]},
    )
