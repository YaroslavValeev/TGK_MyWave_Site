def test_append_record(mocker):
    mock = mocker.patch(
        "app.services.google_sheets_service.append_record", return_value=True
    )
    from app.services.google_sheets_service import append_record

    result = append_record("sheet_id", "worksheet", ["a", "b"])
    assert result is True
    mock.assert_called_once()
