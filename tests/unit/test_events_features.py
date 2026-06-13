"""Events feature flags (Events-1 — default OFF)."""

from app.config.events_features import get_events_feature_flags, is_events_classifier_enabled


class TestEventsFlagsDefaultOff:
    def test_classifier_off_by_default(self, monkeypatch):
        monkeypatch.delenv("EVENTS_CLASSIFIER_ENABLED", raising=False)
        assert is_events_classifier_enabled() is False
        assert get_events_feature_flags() == {"EVENTS_CLASSIFIER_ENABLED": False}

    def test_classifier_on_when_set(self, monkeypatch):
        monkeypatch.setenv("EVENTS_CLASSIFIER_ENABLED", "1")
        assert is_events_classifier_enabled() is True
