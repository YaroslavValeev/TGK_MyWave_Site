"""Events feature flags (Events-1 — default OFF)."""

from app.config.events_features import (
    get_events_feature_flags,
    is_events_api_enabled,
    is_events_classifier_enabled,
    is_events_review_api_enabled,
)


class TestEventsFlagsDefaultOff:
    def test_classifier_off_by_default(self, monkeypatch):
        monkeypatch.delenv("EVENTS_CLASSIFIER_ENABLED", raising=False)
        assert is_events_classifier_enabled() is False

    def test_api_flags_off_by_default(self, monkeypatch):
        for key in (
            "EVENTS_CLASSIFIER_ENABLED",
            "EVENTS_API_ENABLED",
            "EVENTS_REVIEW_API_ENABLED",
        ):
            monkeypatch.delenv(key, raising=False)
        assert get_events_feature_flags() == {
            "EVENTS_CLASSIFIER_ENABLED": False,
            "EVENTS_API_ENABLED": False,
            "EVENTS_REVIEW_API_ENABLED": False,
        }

    def test_review_api_requires_api_master(self, monkeypatch):
        monkeypatch.setenv("EVENTS_API_ENABLED", "0")
        monkeypatch.setenv("EVENTS_REVIEW_API_ENABLED", "1")
        assert is_events_review_api_enabled() is False

    def test_flags_on_when_set(self, monkeypatch):
        monkeypatch.setenv("EVENTS_CLASSIFIER_ENABLED", "1")
        monkeypatch.setenv("EVENTS_API_ENABLED", "1")
        monkeypatch.setenv("EVENTS_REVIEW_API_ENABLED", "true")
        assert is_events_api_enabled() is True
        assert is_events_review_api_enabled() is True
