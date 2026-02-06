"""
Security hardening service for MyWave Safari application
Handles rate limiting, CORS, input validation, and secrets management

Point 16: Security hardening
"""

from typing import Dict, List, Optional, Any
import logging
import os
import hashlib
import hmac
from functools import wraps

from flask import request, jsonify, current_app
from dotenv import load_dotenv

# Try to import optional dependencies
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    HAS_LIMITER = True
except ImportError:
    HAS_LIMITER = False
    Limiter = None

try:
    from flask_cors import CORS

    HAS_CORS = True
except ImportError:
    HAS_CORS = False
    CORS = None

try:
    import bleach

    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False
    bleach = None

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


# =====================================================
# RATE LIMITING
# =====================================================

# Initialize rate limiter (only if Flask-Limiter is installed)
if HAS_LIMITER:
    limiter = Limiter(
        key_func=get_remote_address,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",  # Use Redis in production
    )
else:
    limiter = None
    logger.warning("Flask-Limiter not installed. Rate limiting disabled.")


class RateLimitConfig:
    """Rate limiting configuration for different endpoints"""

    # General API endpoints
    GENERAL_LIMIT = "10/minute"

    # Authentication endpoints (stricter)
    AUTH_LIMIT = "5/minute"
    AUTH_LOGIN_LIMIT = "3/minute"

    # Booking endpoints
    BOOKING_LIST_LIMIT = "30/minute"
    BOOKING_CREATE_LIMIT = "10/minute"

    # Payment endpoints
    PAYMENT_LIMIT = "5/minute"

    # Public endpoints
    PUBLIC_LIMIT = "100/minute"

    @staticmethod
    def get_limit(endpoint_type: str) -> str:
        """Get rate limit for endpoint type"""
        limits = {
            "general": RateLimitConfig.GENERAL_LIMIT,
            "auth": RateLimitConfig.AUTH_LIMIT,
            "auth_login": RateLimitConfig.AUTH_LOGIN_LIMIT,
            "booking_list": RateLimitConfig.BOOKING_LIST_LIMIT,
            "booking_create": RateLimitConfig.BOOKING_CREATE_LIMIT,
            "payment": RateLimitConfig.PAYMENT_LIMIT,
            "public": RateLimitConfig.PUBLIC_LIMIT,
        }
        return limits.get(endpoint_type, RateLimitConfig.GENERAL_LIMIT)


def rate_limited(endpoint_type: str = "general"):
    """
    Decorator for rate limiting endpoints

    Args:
        endpoint_type: Type of endpoint (general, auth, booking, payment, public)

    Example:
        @route('/api/bookings/create')
        @rate_limited('booking_create')
        def create_booking():
            ...
    """
    if not HAS_LIMITER:
        # If limiter not available, return no-op decorator
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                return f(*args, **kwargs)

            return decorated_function

        return decorator

    def decorator(f):
        limit = RateLimitConfig.get_limit(endpoint_type)

        @wraps(f)
        @limiter.limit(limit)
        def decorated_function(*args, **kwargs):
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# =====================================================
# CORS CONFIGURATION
# =====================================================


class CORSConfig:
    """CORS configuration for cross-origin requests"""

    @staticmethod
    def get_cors_config() -> Dict[str, Any]:
        """Get CORS configuration from environment"""
        allowed_origins = os.getenv(
            "CORS_ORIGINS", "http://localhost:3000,http://localhost:5000"
        ).split(",")

        return {
            "origins": allowed_origins,
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "expose_headers": ["Content-Length", "X-Total-Count", "X-Page-Count"],
            "supports_credentials": True,
            "max_age": 86400,  # 24 hours
            "send_wildcard": False,
        }

    @staticmethod
    def init_cors(app):
        """Initialize CORS for Flask app"""
        if not HAS_CORS:
            logger.warning("Flask-CORS not installed. CORS configuration disabled.")
            return

        config = CORSConfig.get_cors_config()
        CORS(app, **config)
        logger.info(f"CORS configured for origins: {config['origins']}")


# =====================================================
# INPUT VALIDATION & SANITIZATION
# =====================================================


class InputValidator:
    """Validate and sanitize user input"""

    # Allowed HTML tags
    ALLOWED_TAGS = [
        "p",
        "br",
        "strong",
        "em",
        "u",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "a",
        "img",
        "blockquote",
    ]

    # Allowed attributes
    ALLOWED_ATTRIBUTES = {
        "a": ["href", "title", "target"],
        "img": ["src", "alt", "title", "width", "height"],
    }

    @staticmethod
    def sanitize_html(html_content: str, strip_tags: bool = False) -> str:
        """
        Sanitize HTML content to prevent XSS

        Args:
            html_content: HTML content to sanitize
            strip_tags: Whether to strip all tags (returns plain text)

        Returns:
            Sanitized HTML content
        """
        if not html_content:
            return ""

        if not HAS_BLEACH:
            # Fallback: remove common dangerous tags
            import re

            if strip_tags:
                return re.sub(r"<[^>]+>", "", html_content)
            return re.sub(
                r"<(script|iframe|object|embed)[^>]*>.*?</\1>",
                "",
                html_content,
                flags=re.IGNORECASE | re.DOTALL,
            )

        if strip_tags:
            return bleach.clean(html_content, tags=[], strip=True)

        return bleach.clean(
            html_content,
            tags=InputValidator.ALLOWED_TAGS,
            attributes=InputValidator.ALLOWED_ATTRIBUTES,
            strip=True,
        )

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format

        Args:
            email: Email address to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Validate phone number format

        Args:
            phone: Phone number to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        # Support various formats
        pattern = r"^\+?[1-9]\d{1,14}$"
        return bool(re.match(pattern, phone.replace("-", "").replace(" ", "")))

    @staticmethod
    def validate_url(url: str) -> bool:
        """
        Validate URL format

        Args:
            url: URL to validate

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r"^https?://[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?:/.*)?$"
        return bool(re.match(pattern, url))

    @staticmethod
    def sanitize_string(text: str, max_length: int = 1000) -> str:
        """
        Sanitize plain text input

        Args:
            text: Text to sanitize
            max_length: Maximum allowed length

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Remove special characters, keep alphanumeric and basic punctuation
        import re

        sanitized = re.sub(r'[<>"]', "", text)

        # Truncate to max length
        return sanitized[:max_length].strip()

    @staticmethod
    def validate_file_upload(filename: str, allowed_extensions: List[str]) -> bool:
        """
        Validate file upload

        Args:
            filename: Name of uploaded file
            allowed_extensions: List of allowed file extensions

        Returns:
            True if valid, False otherwise
        """
        if not filename or "." not in filename:
            return False

        extension = filename.rsplit(".", 1)[1].lower()
        return extension in allowed_extensions


# =====================================================
# SECRETS MANAGEMENT
# =====================================================


class SecretsManager:
    """Manage sensitive configuration and secrets"""

    # Encryption key for sensitive data
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", "dev-key-change-in-production")

    @staticmethod
    def encrypt_secret(value: str) -> str:
        """
        Encrypt a secret value

        Args:
            value: Value to encrypt

        Returns:
            Encrypted value (hex encoded)
        """
        from cryptography.fernet import Fernet

        # In production, use proper key derivation (PBKDF2, bcrypt)
        key = Fernet.generate_key()
        cipher = Fernet(key)

        encrypted = cipher.encrypt(value.encode())
        return encrypted.decode()

    @staticmethod
    def get_secret(key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a secret from environment or config

        Args:
            key: Secret key name (e.g., 'DATABASE_PASSWORD')
            default: Default value if not found

        Returns:
            Secret value or default
        """
        # First try environment variables
        value = os.getenv(key)
        if value:
            return value

        # Then try Flask config
        if current_app:
            value = current_app.config.get(key)
            if value:
                return value

        return default

    @staticmethod
    def validate_api_key(api_key: str) -> bool:
        """
        Validate API key format and existence

        Args:
            api_key: API key to validate

        Returns:
            True if valid, False otherwise
        """
        # API key should be at least 32 characters
        if not api_key or len(api_key) < 32:
            return False

        # Check format (alphanumeric)
        import re

        return bool(re.match(r"^[a-zA-Z0-9]{32,}$", api_key))

    @staticmethod
    def hash_password(password: str, salt: Optional[str] = None) -> tuple:
        """
        Hash password using PBKDF2

        Args:
            password: Password to hash
            salt: Optional salt (generates if not provided)

        Returns:
            Tuple of (hashed_password, salt)
        """
        import secrets

        if salt is None:
            salt = secrets.token_hex(32)

        hashed = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), salt.encode(), 100000  # 100k iterations
        )

        return hashed.hex(), salt

    @staticmethod
    def verify_password(password: str, hashed: str, salt: str) -> bool:
        """
        Verify password against hash

        Args:
            password: Password to verify
            hashed: Stored hash
            salt: Stored salt

        Returns:
            True if password matches, False otherwise
        """
        computed_hash, _ = SecretsManager.hash_password(password, salt)
        return hmac.compare_digest(computed_hash, hashed)


# =====================================================
# SECURITY HEADERS
# =====================================================


class SecurityHeaders:
    """Configure security headers for all responses"""

    @staticmethod
    def init_security_headers(app):
        """Initialize security headers middleware"""

        @app.after_request
        def add_security_headers(response):
            # Prevent XSS attacks
            response.headers["X-Content-Type-Options"] = "nosniff"
            response.headers["X-Frame-Options"] = "SAMEORIGIN"
            response.headers["X-XSS-Protection"] = "1; mode=block"

            # Control referrer information
            response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

            # Control feature access
            response.headers["Permissions-Policy"] = (
                "geolocation=(), microphone=(), camera=()"
            )

            # Content Security Policy
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self'"
            )

            # Cache control for sensitive content
            if "/api/" in request.path or "/auth/" in request.path:
                response.headers["Cache-Control"] = (
                    "no-store, no-cache, must-revalidate, max-age=0"
                )
                response.headers["Pragma"] = "no-cache"

            return response

        logger.info("Security headers initialized")


# =====================================================
# INITIALIZATION
# =====================================================


def init_security(app):
    """
    Initialize all security features
    Call during Flask app initialization

    Args:
        app: Flask application instance
    """
    # Initialize rate limiter if available
    if HAS_LIMITER and limiter:
        limiter.init_app(app)

    # Initialize CORS if available
    if HAS_CORS:
        CORSConfig.init_cors(app)

    # Initialize security headers
    SecurityHeaders.init_security_headers(app)

    # Configure from environment
    app.config["SESSION_COOKIE_SECURE"] = (
        os.getenv("SESSION_COOKIE_SECURE", "True") == "True"
    )
    app.config["SESSION_COOKIE_HTTPONLY"] = (
        os.getenv("SESSION_COOKIE_HTTPONLY", "True") == "True"
    )
    app.config["SESSION_COOKIE_SAMESITE"] = os.getenv("SESSION_COOKIE_SAMESITE", "Lax")

    logger.info("Security hardening initialized")
