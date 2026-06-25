"""Social Mission feature flags (Social-1 — default OFF)."""

from app.config.social_features import (
    get_social_feature_flags,
    is_social_admin_notifications_enabled,
    is_social_applications_enabled,
    is_social_module_enabled,
    is_social_public_stats_enabled,
    is_social_widget_enabled,
)


class TestSocialFlagsDefaultOff:
    def test_all_flags_off_by_default(self, monkeypatch):
        for key in (
            "SOCIAL_MODULE_ENABLED",
            "SOCIAL_WIDGET_ENABLED",
            "SOCIAL_APPLICATIONS_ENABLED",
            "SOCIAL_PUBLIC_STATS_ENABLED",
            "SOCIAL_ADMIN_NOTIFICATIONS_ENABLED",
            "SOCIAL_BOOKING_ENABLED",
        ):
            monkeypatch.delenv(key, raising=False)

        assert get_social_feature_flags() == {
            "SOCIAL_MODULE_ENABLED": False,
            "SOCIAL_WIDGET_ENABLED": False,
            "SOCIAL_APPLICATIONS_ENABLED": False,
            "SOCIAL_PUBLIC_STATS_ENABLED": False,
            "SOCIAL_ADMIN_NOTIFICATIONS_ENABLED": False,
            "SOCIAL_BOOKING_ENABLED": False,
        }

    def test_child_flags_require_module_master(self, monkeypatch):
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "0")
        monkeypatch.setenv("SOCIAL_WIDGET_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_APPLICATIONS_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_PUBLIC_STATS_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_ADMIN_NOTIFICATIONS_ENABLED", "1")

        assert is_social_module_enabled() is False
        assert is_social_widget_enabled() is False
        assert is_social_applications_enabled() is False
        assert is_social_public_stats_enabled() is False
        assert is_social_admin_notifications_enabled() is False
        from app.config.social_features import is_social_booking_enabled

        assert is_social_booking_enabled() is False

    def test_truthy_env_values(self, monkeypatch):
        monkeypatch.setenv("SOCIAL_MODULE_ENABLED", "1")
        monkeypatch.setenv("SOCIAL_WIDGET_ENABLED", "true")
        monkeypatch.setenv("SOCIAL_APPLICATIONS_ENABLED", "yes")
        monkeypatch.setenv("SOCIAL_PUBLIC_STATS_ENABLED", "on")
        monkeypatch.setenv("SOCIAL_ADMIN_NOTIFICATIONS_ENABLED", "True")

        assert is_social_module_enabled() is True
        assert is_social_widget_enabled() is True
        assert is_social_applications_enabled() is True
        assert is_social_public_stats_enabled() is True
        assert is_social_admin_notifications_enabled() is True
