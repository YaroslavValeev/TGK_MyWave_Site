import os
import pytest

pytestmark = pytest.mark.skip(reason="Legacy API: ToolDefinition and call_tool removed from AIGateway")


def test_retry_succeeds_after_transient_failure(monkeypatch):
    pass


def test_retry_exhausted_raises(monkeypatch):
    pass
