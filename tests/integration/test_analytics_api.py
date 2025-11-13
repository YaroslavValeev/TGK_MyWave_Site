import pytest

# Integration test - requires full environment and Google Sheets credentials.
@pytest.mark.skip(reason="Integration test — requires Google Sheets and full dependencies. Run manually when environment is ready.")
def test_post_analytics_log_returns_ok():
    import json
    from app import create_app

    app = create_app('development')
    client = app.test_client()

    payload = {
        "event": "test_event",
        "context": "tests",
        "user_key": "unittest_user",
        "rule_id": "unit_test",
        "item_id": "",
        "type": "test",
        "meta": {"note": "integration test"}
    }

    resp = client.post('/analytics/log', json=payload)
    assert resp.status_code == 200
    data = resp.get_json()
    assert isinstance(data, dict)
    assert data.get('ok') in (True, False)
