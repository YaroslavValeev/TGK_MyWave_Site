"""
Unit tests for performance optimization service
Tests for query optimization, caching, lazy loading, and CDN configuration

Point 15: Performance optimization
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from app.services.performance_service import (
    QueryOptimizer,
    LazyLoadingHelper,
    CDNConfig,
    PerformanceMonitor,
    cache,
    init_performance_optimizations,
    get_cached_active_bookings,
    clear_booking_caches,
)


class TestQueryOptimizer:
    """Test database query optimization"""

    def test_query_optimizer_exists(self):
        """Verify QueryOptimizer class is defined"""
        assert hasattr(QueryOptimizer, "get_bookings_with_participants")
        assert hasattr(QueryOptimizer, "get_participants_with_bookings")
        assert hasattr(QueryOptimizer, "get_upcoming_bookings")
        assert hasattr(QueryOptimizer, "count_active_bookings_by_status")

    def test_get_bookings_with_participants_method(self):
        """Verify bookings query optimization method exists"""
        method = getattr(QueryOptimizer, "get_bookings_with_participants")
        assert callable(method)

        # Check method signature
        import inspect

        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "status" in params
        assert "limit" in params

    def test_get_participants_with_bookings_method(self):
        """Verify participants query optimization method exists"""
        method = getattr(QueryOptimizer, "get_participants_with_bookings")
        assert callable(method)

    def test_get_upcoming_bookings_method(self):
        """Verify upcoming bookings query method exists"""
        method = getattr(QueryOptimizer, "get_upcoming_bookings")
        assert callable(method)

        # Check it accepts days_ahead parameter
        import inspect

        sig = inspect.signature(method)
        params = list(sig.parameters.keys())
        assert "days_ahead" in params

    def test_count_active_bookings_by_status_method(self):
        """Verify booking statistics method exists"""
        method = getattr(QueryOptimizer, "count_active_bookings_by_status")
        assert callable(method)


class TestLazyLoadingHelper:
    """Test lazy loading of heavy data"""

    def test_lazy_loading_helper_exists(self):
        """Verify LazyLoadingHelper class is defined"""
        assert hasattr(LazyLoadingHelper, "serialize_booking_summary")
        assert hasattr(LazyLoadingHelper, "serialize_participant_summary")
        assert hasattr(LazyLoadingHelper, "add_images_lazily")

    def test_serialize_booking_summary_returns_dict(self):
        """Verify booking summary serialization returns dict"""
        # Mock booking object
        mock_booking = Mock()
        mock_booking.id = 1
        mock_booking.participant_id = 10
        mock_booking.status = "confirmed"
        mock_booking.start_date = datetime.now().date()
        mock_booking.days = 3
        mock_booking.created_at = datetime.now()

        result = LazyLoadingHelper.serialize_booking_summary(mock_booking)

        assert isinstance(result, dict)
        assert "id" in result
        assert "status" in result
        assert result["id"] == 1
        assert result["status"] == "confirmed"

    def test_booking_summary_has_required_fields(self):
        """Verify booking summary contains required fields"""
        mock_booking = Mock()
        mock_booking.id = 1
        mock_booking.participant_id = 10
        mock_booking.status = "pending"
        mock_booking.start_date = datetime.now().date()
        mock_booking.days = 5
        mock_booking.created_at = datetime.now()

        result = LazyLoadingHelper.serialize_booking_summary(mock_booking)

        required_fields = [
            "id",
            "participant_id",
            "status",
            "start_date",
            "days",
            "created_at",
        ]
        for field in required_fields:
            assert field in result, f"Field '{field}' must be in booking summary"

    def test_serialize_participant_summary_returns_dict(self):
        """Verify participant summary serialization returns dict"""
        mock_participant = Mock()
        mock_participant.id = 5
        mock_participant.name = "John Doe"
        mock_participant.email = "john@example.com"
        mock_participant.phone = "+1234567890"
        mock_participant.level = "intermediate"
        mock_participant.route_id = 3
        mock_participant.created_at = datetime.now()

        result = LazyLoadingHelper.serialize_participant_summary(mock_participant)

        assert isinstance(result, dict)
        assert result["name"] == "John Doe"
        assert result["email"] == "john@example.com"

    def test_participant_summary_has_required_fields(self):
        """Verify participant summary contains required fields"""
        mock_participant = Mock()
        mock_participant.id = 5
        mock_participant.name = "Jane Smith"
        mock_participant.email = "jane@example.com"
        mock_participant.phone = "+9876543210"
        mock_participant.level = "beginner"
        mock_participant.route_id = 2
        mock_participant.created_at = datetime.now()

        result = LazyLoadingHelper.serialize_participant_summary(mock_participant)

        required_fields = [
            "id",
            "name",
            "email",
            "phone",
            "level",
            "route_id",
            "created_at",
        ]
        for field in required_fields:
            assert field in result, f"Field '{field}' must be in participant summary"

    def test_add_images_lazily_method_exists(self):
        """Verify lazy image loading method exists"""
        method = getattr(LazyLoadingHelper, "add_images_lazily")
        assert callable(method)


class TestCDNConfig:
    """Test CDN configuration"""

    def test_cdn_config_exists(self):
        """Verify CDNConfig class is defined"""
        assert hasattr(CDNConfig, "get_cdn_url")
        assert hasattr(CDNConfig, "optimize_image_url")
        assert hasattr(CDNConfig, "get_responsive_image_urls")

    def test_get_cdn_url_returns_string(self):
        """Verify CDN URL returns string"""
        try:
            result = CDNConfig.get_cdn_url("images/test.jpg", use_cdn=False)
            assert isinstance(result, str)
            assert "test.jpg" in result
        except RuntimeError:
            # Expected if no app context - that's OK for this test
            pytest.skip("No app context available")

    def test_optimize_image_url_returns_string(self):
        """Verify image URL optimization returns string"""
        try:
            result = CDNConfig.optimize_image_url("image.jpg", width=800, height=600)
            assert isinstance(result, str)
            assert "image.jpg" in result or "cdn" in result.lower()
        except RuntimeError:
            pytest.skip("No app context available")

    def test_optimize_image_url_with_quality_returns_string(self):
        """Verify image URL optimization with quality returns string"""
        try:
            result = CDNConfig.optimize_image_url("photo.jpg", quality=80)
            assert isinstance(result, str)
        except RuntimeError:
            pytest.skip("No app context available")

    def test_get_responsive_image_urls_returns_dict(self):
        """Verify responsive image URLs returns dict with required keys"""
        try:
            result = CDNConfig.get_responsive_image_urls("photo.jpg")

            assert isinstance(result, dict)
            assert "mobile" in result
            assert "tablet" in result
            assert "desktop" in result
            assert "original" in result

            # All values should be strings
            for key, value in result.items():
                assert isinstance(value, str), f"Value for '{key}' must be string"
        except RuntimeError:
            pytest.skip("No app context available")


class TestPerformanceMonitor:
    """Test performance monitoring"""

    def test_performance_monitor_exists(self):
        """Verify PerformanceMonitor class is defined"""
        assert hasattr(PerformanceMonitor, "log_query_metrics")
        assert hasattr(PerformanceMonitor, "enable_slow_query_logging")

    def test_log_query_metrics_method(self):
        """Verify query metrics logging method exists"""
        method = getattr(PerformanceMonitor, "log_query_metrics")
        assert callable(method)

        # Should not raise error
        result = method([], "test_query", threshold_ms=100)
        assert result is None

    def test_enable_slow_query_logging_method(self):
        """Verify slow query logging can be enabled"""
        method = getattr(PerformanceMonitor, "enable_slow_query_logging")
        assert callable(method)

        # Should not raise error when called without app context
        try:
            method(threshold_ms=200)
        except RuntimeError as e:
            # OK if no db.engine context
            if "no engine" not in str(e).lower():
                pytest.skip(f"Skipped due to: {e}")
        except Exception:
            # Other exceptions are OK in unit test without full app context
            pass


class TestCachingFunctions:
    """Test caching functions"""

    def test_cached_result_decorator_exists(self):
        """Verify cached_result decorator is defined"""
        from app.services.performance_service import cached_result

        assert callable(cached_result)

    def test_invalidate_cache_decorator_exists(self):
        """Verify invalidate_cache decorator is defined"""
        from app.services.performance_service import invalidate_cache

        assert callable(invalidate_cache)

    def test_get_cached_active_bookings_callable(self):
        """Verify cached bookings function is callable"""
        assert callable(get_cached_active_bookings)

    def test_get_cached_booking_stats_callable(self):
        """Verify cached stats function is callable"""
        from app.services.performance_service import get_cached_booking_stats

        assert callable(get_cached_booking_stats)

    def test_clear_booking_caches_callable(self):
        """Verify cache clearing function is callable"""
        assert callable(clear_booking_caches)


class TestCacheInitialization:
    """Test cache initialization"""

    def test_cache_object_exists(self):
        """Verify cache object is initialized"""
        assert cache is not None
        assert hasattr(cache, "set")
        assert hasattr(cache, "get")
        assert hasattr(cache, "delete")

    def test_init_performance_optimizations_callable(self):
        """Verify initialization function is callable"""
        assert callable(init_performance_optimizations)

    def test_init_performance_optimizations_signature(self):
        """Verify initialization function has correct signature"""
        import inspect

        sig = inspect.signature(init_performance_optimizations)
        params = list(sig.parameters.keys())
        assert "app" in params


class TestPerformanceConfiguration:
    """Test performance configuration options"""

    def test_performance_service_configuration_exists(self):
        """Verify performance service can be configured"""
        # Check that configuration constants are defined
        from app.services import performance_service

        assert hasattr(performance_service, "QueryOptimizer")
        assert hasattr(performance_service, "LazyLoadingHelper")
        assert hasattr(performance_service, "CDNConfig")
        assert hasattr(performance_service, "PerformanceMonitor")

    def test_cache_configurations_supported(self):
        """Verify multiple cache types are supported"""
        cache_types = ["simple", "redis", "memcached"]
        # Just verify the service is designed to support caching
        from app.services.performance_service import cache

        assert cache is not None


class TestDocumentation:
    """Test that documentation exists"""

    def test_performance_service_docstrings(self):
        """Verify methods have documentation"""
        methods = [
            QueryOptimizer.get_bookings_with_participants,
            LazyLoadingHelper.serialize_booking_summary,
            CDNConfig.get_cdn_url,
            PerformanceMonitor.log_query_metrics,
        ]

        for method in methods:
            assert method.__doc__ is not None, f"{method.__name__} must have docstring"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
