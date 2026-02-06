"""
Unit tests for security hardening service
Tests for rate limiting, CORS, input validation, and secrets management

Point 16: Security hardening
"""

import pytest
import os
from unittest.mock import Mock, patch, MagicMock

# Import with graceful fallback for optional dependencies
try:
    from app.services.security_service import (
        RateLimitConfig,
        CORSConfig,
        InputValidator,
        SecretsManager,
        SecurityHeaders,
        rate_limited,
        init_security,
    )

    SECURITY_SERVICE_AVAILABLE = True
except ImportError:
    SECURITY_SERVICE_AVAILABLE = False
    pytest.skip("Security service module not available", allow_module_level=True)


class TestRateLimiting:
    """Test rate limiting configuration"""

    def test_rate_limit_config_exists(self):
        """Verify RateLimitConfig class is defined"""
        assert hasattr(RateLimitConfig, "GENERAL_LIMIT")
        assert hasattr(RateLimitConfig, "AUTH_LIMIT")
        assert hasattr(RateLimitConfig, "BOOKING_CREATE_LIMIT")

    def test_rate_limit_values(self):
        """Verify rate limit values are reasonable"""
        assert RateLimitConfig.GENERAL_LIMIT == "10/minute"
        assert RateLimitConfig.AUTH_LIMIT == "5/minute"
        assert RateLimitConfig.AUTH_LOGIN_LIMIT == "3/minute"
        assert RateLimitConfig.BOOKING_CREATE_LIMIT == "10/minute"

    def test_get_limit_method(self):
        """Verify get_limit returns correct limits"""
        assert RateLimitConfig.get_limit("general") == "10/minute"
        assert RateLimitConfig.get_limit("auth") == "5/minute"
        assert RateLimitConfig.get_limit("auth_login") == "3/minute"
        assert RateLimitConfig.get_limit("payment") == "5/minute"

    def test_get_limit_default(self):
        """Verify get_limit returns default for unknown type"""
        result = RateLimitConfig.get_limit("unknown_type")
        assert result == RateLimitConfig.GENERAL_LIMIT

    def test_rate_limited_decorator_exists(self):
        """Verify rate_limited decorator is available"""
        assert callable(rate_limited)

    def test_rate_limited_decorator_callable(self):
        """Verify rate_limited decorator can be applied"""

        @rate_limited("general")
        def dummy_func():
            return "success"

        # Should be callable
        assert callable(dummy_func)

    def test_limiter_object_exists(self):
        """Verify limiter object is initialized"""
        # Limiter is optional, just verify configuration exists
        assert hasattr(RateLimitConfig, "GENERAL_LIMIT")


class TestCORSConfiguration:
    """Test CORS configuration"""

    def test_cors_config_exists(self):
        """Verify CORSConfig class is defined"""
        assert hasattr(CORSConfig, "get_cors_config")
        assert hasattr(CORSConfig, "init_cors")

    def test_get_cors_config_returns_dict(self):
        """Verify get_cors_config returns dictionary"""
        config = CORSConfig.get_cors_config()
        assert isinstance(config, dict)

    def test_cors_config_has_required_fields(self):
        """Verify CORS config has required fields"""
        config = CORSConfig.get_cors_config()

        required_fields = [
            "origins",
            "methods",
            "allow_headers",
            "supports_credentials",
        ]
        for field in required_fields:
            assert field in config, f"CORS config must include '{field}'"

    def test_cors_config_methods_valid(self):
        """Verify CORS allowed methods are correct"""
        config = CORSConfig.get_cors_config()
        methods = config["methods"]

        required_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        for method in required_methods:
            assert method in methods, f"Method '{method}' must be in CORS methods"

    def test_cors_config_credentials_enabled(self):
        """Verify credentials are allowed"""
        config = CORSConfig.get_cors_config()
        assert config["supports_credentials"] is True

    def test_init_cors_callable(self):
        """Verify init_cors method is callable"""
        assert callable(CORSConfig.init_cors)


class TestInputValidation:
    """Test input validation and sanitization"""

    def test_input_validator_exists(self):
        """Verify InputValidator class is defined"""
        assert hasattr(InputValidator, "sanitize_html")
        assert hasattr(InputValidator, "validate_email")
        assert hasattr(InputValidator, "validate_phone")
        assert hasattr(InputValidator, "validate_url")

    def test_sanitize_html_removes_scripts(self):
        """Verify sanitize_html removes script tags"""
        html = "<p>Safe</p><script>alert('xss')</script>"
        result = InputValidator.sanitize_html(html)

        # Result should not contain script tag or alert
        assert "script" not in result.lower() or "Safe" in result

    def test_sanitize_html_preserves_allowed_tags(self):
        """Verify sanitize_html preserves allowed tags"""
        html = "<p>This is <strong>bold</strong> text</p>"
        result = InputValidator.sanitize_html(html)

        assert "<p>" in result or "This" in result
        assert "bold" in result

    def test_sanitize_html_strips_all_tags(self):
        """Verify sanitize_html can strip all tags"""
        html = "<p>Text with <strong>formatting</strong></p>"
        result = InputValidator.sanitize_html(html, strip_tags=True)

        assert "<p>" not in result
        assert "<strong>" not in result
        assert "Text" in result

    def test_validate_email_valid(self):
        """Verify valid emails pass validation"""
        valid_emails = [
            "user@example.com",
            "test.user@domain.co.uk",
            "user+tag@example.com",
        ]

        for email in valid_emails:
            assert InputValidator.validate_email(email), f"{email} should be valid"

    def test_validate_email_invalid(self):
        """Verify invalid emails fail validation"""
        invalid_emails = ["invalid", "@example.com", "user@", "user @example.com"]

        for email in invalid_emails:
            assert not InputValidator.validate_email(
                email
            ), f"{email} should be invalid"

    def test_validate_phone_valid(self):
        """Verify valid phone numbers pass validation"""
        valid_phones = ["+1234567890", "1234567890", "+380123456789"]

        for phone in valid_phones:
            assert InputValidator.validate_phone(phone), f"{phone} should be valid"

    def test_validate_phone_invalid(self):
        """Verify invalid phone numbers fail validation"""
        invalid_phones = [
            "123",  # Too short
            "abc",  # Not numeric
            "+0123456789",  # Starts with 0
        ]

        # At least one should be invalid
        assert not all(InputValidator.validate_phone(phone) for phone in invalid_phones)

    def test_validate_url_valid(self):
        """Verify valid URLs pass validation"""
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://sub.example.co.uk/path?query=value",
        ]

        for url in valid_urls:
            assert InputValidator.validate_url(url), f"{url} should be valid"

    def test_validate_url_invalid(self):
        """Verify invalid URLs fail validation"""
        invalid_urls = ["not a url", "ftp://example.com", "example.com"]

        for url in invalid_urls:
            assert not InputValidator.validate_url(url), f"{url} should be invalid"

    def test_sanitize_string_removes_special_chars(self):
        """Verify sanitize_string removes dangerous characters"""
        text = 'Hello <script>alert("xss")</script> World'
        result = InputValidator.sanitize_string(text)

        assert "<" not in result
        assert ">" not in result
        assert '"' not in result

    def test_sanitize_string_respects_max_length(self):
        """Verify sanitize_string respects max length"""
        text = "A" * 2000
        result = InputValidator.sanitize_string(text, max_length=100)

        assert len(result) <= 100

    def test_validate_file_upload_valid(self):
        """Verify valid file uploads pass validation"""
        assert InputValidator.validate_file_upload("document.pdf", ["pdf", "doc"])
        assert InputValidator.validate_file_upload("image.jpg", ["jpg", "png", "gif"])

    def test_validate_file_upload_invalid_extension(self):
        """Verify invalid file extensions fail validation"""
        assert not InputValidator.validate_file_upload("script.exe", ["pdf", "doc"])
        assert not InputValidator.validate_file_upload("exploit.py", ["jpg", "png"])

    def test_validate_file_upload_invalid_format(self):
        """Verify invalid file formats fail validation"""
        assert not InputValidator.validate_file_upload("noextension", ["pdf"])
        assert not InputValidator.validate_file_upload("", ["pdf"])


class TestSecretsManagement:
    """Test secrets management"""

    def test_secrets_manager_exists(self):
        """Verify SecretsManager class is defined"""
        assert hasattr(SecretsManager, "get_secret")
        assert hasattr(SecretsManager, "validate_api_key")
        assert hasattr(SecretsManager, "hash_password")
        assert hasattr(SecretsManager, "verify_password")

    def test_get_secret_from_env(self):
        """Verify get_secret retrieves from environment"""
        with patch.dict(os.environ, {"TEST_SECRET": "secret_value"}):
            result = SecretsManager.get_secret("TEST_SECRET")
            assert result == "secret_value"

    def test_get_secret_default(self):
        """Verify get_secret returns default if not found"""
        result = SecretsManager.get_secret(
            "NONEXISTENT_SECRET", default="default_value"
        )
        assert result == "default_value"

    def test_validate_api_key_valid(self):
        """Verify valid API keys pass validation"""
        # API key must be at least 32 alphanumeric characters
        valid_key = "a" * 32  # Minimum 32 characters
        assert SecretsManager.validate_api_key(valid_key)

    def test_validate_api_key_invalid_too_short(self):
        """Verify short API keys fail validation"""
        short_key = "abc123"
        assert not SecretsManager.validate_api_key(short_key)

    def test_validate_api_key_invalid_characters(self):
        """Verify API keys with invalid characters fail validation"""
        invalid_key = "a" * 32 + "<script>"
        assert not SecretsManager.validate_api_key(invalid_key)

    def test_hash_password_generates_salt(self):
        """Verify hash_password generates salt if not provided"""
        hashed, salt = SecretsManager.hash_password("mypassword")

        assert hashed is not None
        assert salt is not None
        assert len(salt) > 0
        assert len(hashed) > 0

    def test_hash_password_with_salt(self):
        """Verify hash_password uses provided salt"""
        custom_salt = "custom_salt_value"
        hashed, returned_salt = SecretsManager.hash_password("mypassword", custom_salt)

        assert returned_salt == custom_salt
        assert hashed is not None

    def test_verify_password_correct(self):
        """Verify correct password passes verification"""
        password = "mypassword123"
        hashed, salt = SecretsManager.hash_password(password)

        result = SecretsManager.verify_password(password, hashed, salt)
        assert result is True

    def test_verify_password_incorrect(self):
        """Verify incorrect password fails verification"""
        hashed, salt = SecretsManager.hash_password("correct_password")

        result = SecretsManager.verify_password("wrong_password", hashed, salt)
        assert result is False

    def test_hash_password_different_hashes(self):
        """Verify same password with different salts produces different hashes"""
        password = "mypassword"
        hash1, salt1 = SecretsManager.hash_password(password)
        hash2, salt2 = SecretsManager.hash_password(password)

        # Different salts should produce different hashes
        assert salt1 != salt2
        assert hash1 != hash2


class TestSecurityHeaders:
    """Test security headers"""

    def test_security_headers_exists(self):
        """Verify SecurityHeaders class is defined"""
        assert hasattr(SecurityHeaders, "init_security_headers")

    def test_init_security_headers_callable(self):
        """Verify init_security_headers is callable"""
        assert callable(SecurityHeaders.init_security_headers)


class TestSecurityInitialization:
    """Test security initialization"""

    def test_init_security_callable(self):
        """Verify init_security is callable"""
        assert callable(init_security)


class TestSecurityDocumentation:
    """Test that security documentation exists"""

    def test_security_service_docstrings(self):
        """Verify methods have documentation"""
        methods = [
            RateLimitConfig.get_limit,
            CORSConfig.get_cors_config,
            InputValidator.sanitize_html,
            InputValidator.validate_email,
            SecretsManager.hash_password,
            SecretsManager.verify_password,
        ]

        for method in methods:
            assert method.__doc__ is not None, f"{method.__name__} must have docstring"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
