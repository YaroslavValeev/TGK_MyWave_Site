import pytest


def test_register_and_call_tool_with_api_key(client, app):
    # Enable API key enforcement and rate limiting off (for this test)
    app.config["AI_GATEWAY_REQUIRE_API_KEY"] = True
    app.config["AI_GATEWAY_API_KEYS"] = ["adminkey"]
    app.config["AI_GATEWAY_ENABLE_RATE_LIMIT"] = False

    headers = {"Authorization": "Bearer adminkey"}

    # Register a test tool named 'echo2'
    r = client.post(
        "/api/ai/gateway/tools/register_test", json={"name": "echo2"}, headers=headers
    )
    assert r.status_code == 200
    j = r.get_json()
    assert j.get("ok") is True
    assert j.get("tool") == "echo2"

    # Now ask the gateway to call that tool using the mock function-calling format
    payload = '__call_tool__:echo2:{"foo":"bar"}'
    r2 = client.post(
        "/api/ai/gateway/message", json={"message": payload}, headers=headers
    )
    assert r2.status_code == 200
    j2 = r2.get_json()
    # Expect a tool_result with the echoed payload
    assert j2.get("type") == "tool_result"
    assert j2.get("tool") == "echo2"
    assert isinstance(j2.get("result"), dict)
    assert j2["result"].get("echo", {}).get("foo") == "bar"


def test_register_tool_requires_auth(client, app):
    # Ensure requiring key blocks anonymous register
    app.config["AI_GATEWAY_REQUIRE_API_KEY"] = True
    app.config["AI_GATEWAY_API_KEYS"] = ["adminkey"]

    r = client.post("/api/ai/gateway/tools/register_test", json={"name": "x"})
    assert r.status_code == 401
