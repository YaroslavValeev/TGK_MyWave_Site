import json


def test_calc_save_writes_row(client):
    # disable CSRF for this test client (test config may not disable it)
    client.application.config["WTF_CSRF_ENABLED"] = False
    payload = {
        "phone": "+79990001122",
        "city": "Moscow",
        "tags": ["wakesurf", "beginner"],
        "inputs": {"weight": 75, "height": 180},
        "result": {"score": 42},
    }

    resp = client.post("/api/calculator/save", json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True

    # ensure append_record was called and row contains our data
    from app.services import google_sheets_service

    assert google_sheets_service.append_record.called
    args = google_sheets_service.append_record.call_args[0]
    # signature: append_record(spreadsheet_id, worksheet_name, values)
    assert len(args) >= 3
    sheet_name = args[1]
    row = args[2]
    assert sheet_name == "Calculator_Results"
    # row format: [ts, phone, city, tags, inputs, result]
    assert row[1] == payload["phone"]
    assert row[2] == payload["city"]
    assert row[3] == ", ".join(payload["tags"])
    # inputs/result stored as JSON strings
    inputs_parsed = json.loads(row[4])
    result_parsed = json.loads(row[5])
    assert inputs_parsed == payload["inputs"]
    assert result_parsed == payload["result"]


def test_calc_history_filters_by_phone(client, mocker):
    # Prepare fake records from Google Sheets
    fake_records = [
        {
            "ts": "t1",
            "phone": "+79990001122",
            "city": "Moscow",
            "tags": "a",
            "inputs": "{}",
            "result": "{}",
        },
        {
            "ts": "t2",
            "phone": "+70000000000",
            "city": "SPb",
            "tags": "b",
            "inputs": "{}",
            "result": "{}",
        },
    ]
    mocker.patch(
        "app.services.google_sheets_service.read_records", return_value=fake_records
    )

    resp = client.get("/api/calculator/history?phone=%2B79990001122")
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("ok") is True
    history = data.get("history")
    assert isinstance(history, list)
    assert len(history) == 1
    assert history[0]["phone"] == "+79990001122"
