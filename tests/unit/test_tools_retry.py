import os
import pytest

from app.ai.core_gateway import create_default_gateway, ToolDefinition


def test_retry_succeeds_after_transient_failure(monkeypatch):
    # allow up to 3 retries
    monkeypatch.setenv("TOOL_RETRY_COUNT", "3")
    monkeypatch.setenv("TOOL_RETRY_BACKOFF_SEC", "0")

    gateway = create_default_gateway()

    calls = {"n": 0}

    def flaky(payload):
        calls["n"] += 1
        # fail first two times, succeed third
        if calls["n"] < 3:
            raise RuntimeError("temporary")
        return {"ok": True, "attempts": calls["n"]}

    gateway.register_tool(ToolDefinition(name="flaky", description="test"), flaky)

    res = gateway.call_tool("flaky", {})
    assert res["ok"] is True
    assert res["attempts"] == 3


def test_retry_exhausted_raises(monkeypatch):
    monkeypatch.setenv("TOOL_RETRY_COUNT", "1")
    monkeypatch.setenv("TOOL_RETRY_BACKOFF_SEC", "0")

    gateway = create_default_gateway()

    def always_fail(payload):
        raise RuntimeError("boom")

    gateway.register_tool(
        ToolDefinition(name="always_fail", description="test"), always_fail
    )

    with pytest.raises(RuntimeError):
        gateway.call_tool("always_fail", {})
