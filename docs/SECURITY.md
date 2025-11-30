# MyWave Security Hardening Guide

## Overview

This document describes the comprehensive security implementation for MyWave, including rate limiting, CORS configuration, input validation, secrets management, and security headers. All security components are implemented in `app/services/security_service.py`.

## Architecture

The security layer is built on a modular design with the following core components:

```text
security_service.py
├── RateLimitConfig (Rate Limiting)
├── CORSConfig (Cross-Origin Resource Sharing)
├── InputValidator (Input Validation & Sanitization)
├── SecretsManager (Secrets & Encryption)
└── SecurityHeaders (HTTP Security Headers)
```

---

## 1. Rate Limiting

### Overview

Rate limiting prevents abuse by restricting the number of requests a client can make within a specific time window. MyWave implements multiple rate-limiting strategies for different endpoint types.

### Configuration

The `RateLimitConfig` class defines rate limits for different endpoint categories:

```python
RateLimitConfig = {
    'general': '100 per hour',        # Default rate limit
    'auth': '5 per minute',           # Login/auth endpoints
    'booking': '20 per hour',         # Booking creation
    'payment': '10 per hour',         # Payment processing
    'public': '200 per hour',         # Public API endpoints
    'ai_chat': '30 per day',          # AI chat assistant
    'calendar': '50 per hour'         # Calendar sync operations
}
```

### Implementation

Apply rate limiting to endpoints using the `@rate_limited()` decorator:

```python
from app.services.security_service import rate_limited

@app.route('/api/auth/login', methods=['POST'])
@rate_limited('auth')
def login():
    """Login endpoint with strict rate limiting (5 per minute)"""
    return handle_login()

@app.route('/api/bookings', methods=['POST'])
@rate_limited('booking')
def create_booking():
    """Booking creation with per-hour limit"""
    return handle_booking()
```

### Behavior

- **When limit is exceeded**: Returns `429 Too Many Requests` status
- **Response headers**: Includes `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`
- **Grace period**: Graceful fallback if Flask-Limiter not installed (logging warning)

### Bypass

Rate limiting is skipped if `RATELIMIT_DISABLED=true` in environment variables (development only).

---

## 2. CORS Configuration

### Overview​

Cross-Origin Resource Sharing (CORS) controls which external domains can access MyWave APIs. Strict CORS configuration prevents unauthorized cross-origin requests.

### Configuration​

The `CORSConfig` class manages CORS settings:

```python
CORSConfig = {
    'origins': ['https://example.com', 'https://www.example.com'],
    'methods': ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
    'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With'],
    'expose_headers': ['Content-Range', 'X-Content-Range'],
    'max_age': 3600,           # Preflight cache duration (seconds)
    'supports_credentials': True,  # Allow cookies in CORS requests
    'strict': True              # Enforce strict CORS validation
}
```

### Implementation​

Initialize CORS in your Flask application:

```python
from flask import Flask
from app.services.security_service import init_cors

app = Flask(__name__)
init_cors(app)  # Apply CORS configuration
```

### Allowed Origins

Configure allowed origins via environment variable:

```bash
CORS_ORIGINS="https://example.com,https://www.example.com"
```

### Behavior​

- **Preflight requests**: OPTIONS requests are automatically handled
- **Credentials**: Cookies and Authorization headers are supported
- **Invalid origins**: Rejected with CORS error (browser blocks response)
- **Grace period**: Graceful fallback if Flask-CORS not installed

---

## 3. Input Validation & Sanitization

### Overview​

The `InputValidator` class provides comprehensive input validation and sanitization to prevent injection attacks (SQL, XSS, etc.).

### Methods

#### 3.1 HTML Sanitization

```python
from app.services.security_service import InputValidator

# Remove dangerous HTML tags (scripts, iframes, etc.)
clean_html = InputValidator.sanitize_html('<p>Hello</p><script>alert("xss")</script>')
# Result: '<p>Hello</p>' (script tag removed)

# Strip all HTML tags
text_only = InputValidator.sanitize_html('<p>Hello <b>world</b></p>', strip_all=True)
# Result: 'Hello world'
```

**Allowed tags**: `<p>`, `<b>`, `<i>`, `<u>`, `<strong>`, `<em>`, `<a>`, `<ul>`, `<ol>`, `<li>`, `<blockquote>`, `<code>`, `<br>`

**Blocked tags**: `<script>`, `<iframe>`, `<object>`, `<embed>`, `<form>`, `<input>`, `<style>`, `<link>`

#### 3.2 Email Validation

```python
# RFC 5322 compliant email validation
assert InputValidator.validate_email('user@example.com')  # Valid
assert not InputValidator.validate_email('invalid.email')  # Invalid
```

**Format**: Must contain exactly one `@` with local and domain parts

#### 3.3 Phone Number Validation

```python
# International phone format validation
assert InputValidator.validate_phone('+1-555-123-4567')  # Valid
assert InputValidator.validate_phone('(555) 123-4567')   # Valid
assert not InputValidator.validate_phone('123')           # Too short
```

**Formats accepted**:
- `+1-555-123-4567` (international)
- `(555) 123-4567` (US format)
- `555.123.4567` (dot-separated)
- `5551234567` (digits only, min 10 digits)

#### 3.4 URL Validation

```python
# URL format validation
assert InputValidator.validate_url('https://example.com')      # Valid
assert InputValidator.validate_url('https://example.com/path') # Valid
assert not InputValidator.validate_url('not a url')            # Invalid
```

**Requirements**:
- Must start with `http://` or `https://`
- Valid domain structure
- No dangerous protocols (`javascript:`, `data:`, etc.)

#### 3.5 String Sanitization

```python
# Remove special characters and limit length
clean = InputValidator.sanitize_string('Hello<script>alert</script>', max_length=50)
# Result: 'Helloscriptalert' (max 50 chars, special chars removed)
```

**Special chars removed**: `<`, `>`, `&`, `'`, `"`, `;`, `,`, `|`, etc.

#### 3.6 File Upload Validation

```python
# Validate file uploads
valid, message = InputValidator.validate_file_upload(
    filename='document.pdf',
    file_size=1024000,  # 1MB
    allowed_extensions=['pdf', 'docx'],
    max_size_mb=10
)

if valid:
    print("File upload allowed")
else:
    print(f"Upload rejected: {message}")
```

**Default allowed extensions**: `pdf`, `docx`, `xlsx`, `txt`, `csv`, `jpg`, `png`, `gif`

**Default max size**: 10 MB

### Usage Example

```python
from flask import request
from app.services.security_service import InputValidator

@app.route('/api/profile', methods=['POST'])
def update_profile():
    data = request.json

    # Validate and sanitize inputs
    if not InputValidator.validate_email(data.get('email')):
        return {'error': 'Invalid email'}, 400

    if not InputValidator.validate_phone(data.get('phone')):
        return {'error': 'Invalid phone'}, 400

    # Sanitize HTML content
    bio = InputValidator.sanitize_html(data.get('bio', ''))

    # Validate file upload
    if 'avatar' in request.files:
        valid, msg = InputValidator.validate_file_upload(
            request.files['avatar'].filename,
            len(request.files['avatar'].read())
        )
        if not valid:
            return {'error': msg}, 400

    return {'status': 'updated'}
```

---

## 4. Secrets Management

### Overview​

The `SecretsManager` class handles secure storage and management of sensitive data including passwords, API keys, and secrets.

### Methods​

#### 4.1 Secret Retrieval

```python
from app.services.security_service import SecretsManager

# Get secret from environment variables (safe default)
api_key = SecretsManager.get_secret('API_KEY', default='default_key')

# Retrieve without default (raises error if not found)
db_password = SecretsManager.get_secret('DATABASE_PASSWORD')
```

#### 4.2 API Key Validation

```python
# Validate API key format and length (min 32 alphanumeric characters)
valid_key = 'a' * 32  # 32+ character alphanumeric string
assert SecretsManager.validate_api_key(valid_key)  # True

# Invalid keys
assert not SecretsManager.validate_api_key('short')      # Too short
assert not SecretsManager.validate_api_key('key!@#')     # Invalid chars
```

**Requirements**:
- Minimum 32 characters
- Alphanumeric only (no special characters)
- Can contain uppercase and lowercase letters, digits

#### 4.3 Password Hashing (PBKDF2)

```python
# Hash a password with automatic salt generation
password = 'MySecurePassword123!'
hashed, salt = SecretsManager.hash_password(password)

# Hash with specific salt
hashed, used_salt = SecretsManager.hash_password(password, salt=salt)

# Verify password
is_correct = SecretsManager.verify_password('MySecurePassword123!', hashed)
assert is_correct  # True

# Wrong password
assert not SecretsManager.verify_password('WrongPassword', hashed)
```

**Algorithm**: PBKDF2-HMAC-SHA256
- **Iterations**: 100,000
- **Key length**: 32 bytes
- **Salt length**: 16 bytes (auto-generated if not provided)

#### 4.4 Secret Encryption (Fernet)

```python
# Encrypt sensitive data
secret_text = 'Sensitive database credentials'
encrypted = SecretsManager.encrypt_secret(secret_text)

# Decrypt (requires ENCRYPTION_KEY environment variable)
decrypted = SecretsManager.get_secret('ENCRYPTION_KEY')
```

**Encryption**: Fernet (symmetric, authenticated)
- Uses `ENCRYPTION_KEY` from environment
- Provides both encryption and authentication
- Prevents tampering

### Configuration​

Set the following environment variables:

```bash
# Encryption key (must be 44 characters, base64 URL-safe)
ENCRYPTION_KEY="your-44-char-base64-fernet-key"

# API key for validating requests
API_KEY="a" * 32  # At least 32 alphanumeric characters

# Database password (stored securely)
DATABASE_PASSWORD="secure_password"
```

### Usage Example​

```python
from app.services.security_service import SecretsManager

# Register user with password hashing
def register_user(username, password):
    # Hash password securely
    hashed_password, salt = SecretsManager.hash_password(password)

    # Store hashed password in database
    user = User(username=username, password=hashed_password, salt=salt)
    db.session.add(user)
    db.session.commit()

    return user

# Authenticate user
def authenticate_user(username, password):
    user = User.query.filter_by(username=username).first()

    if user and SecretsManager.verify_password(password, user.password):
        return user

    return None

# Validate API requests
def validate_api_request(api_key):
    if not SecretsManager.validate_api_key(api_key):
        return False, 'Invalid API key format'

    # Additional checks...
    return True, 'Valid'
```

---

## 5. Security Headers

### Overview​

Security headers are HTTP response headers that instruct browsers to implement additional security controls. MyWave implements 8 essential security headers.

### Headers

| Header | Value | Purpose |
|--------|-------|---------|
| `X-Content-Type-Options` | `nosniff` | Prevents MIME type sniffing attacks |
| `X-Frame-Options` | `DENY` | Prevents clickjacking by forbidding iframe embedding |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'` | Restricts content sources (prevents XSS) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Controls referrer information |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | Restricts browser features |
| `X-XSS-Protection` | `1; mode=block` | Legacy XSS filter (browsers that support it) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | Forces HTTPS for 1 year |
| `Expect-CT` | `max-age=86400, enforce` | Certificate transparency enforcement |

### Implementation​

Initialize security headers in your Flask application:

```python
from flask import Flask
from app.services.security_service import init_security_headers

app = Flask(__name__)
init_security_headers(app)  # Apply all security headers
```

### Customization

Modify headers by adjusting the `SecurityHeaders` class:

```python
# In app/services/security_service.py
SecurityHeaders = {
    'X-Content-Type-Options': 'nosniff',
    'X-Frame-Options': 'SAMEORIGIN',  # Allow same-origin iframes
    'Content-Security-Policy': 'default-src "self"; ...',
    # ... other headers
}
```

### Browser Support

- **Modern browsers**: Full support for all headers
- **Legacy browsers**: Graceful degradation (headers ignored)
- **IE9-IE10**: Limited support for CSP

---

## 6. Initialization

### Overview​

The `init_security()` function initializes all security components in a single call.

### Usage

```python
from flask import Flask
from app.services.security_service import init_security

app = Flask(__name__)

# Initialize all security components
init_security(app)

# Application now has:
# - Rate limiting enabled
# - CORS configured
# - Security headers applied
# - Input validation available
# - Secrets management initialized
```

### Optional Dependencies

Some security features require additional packages:

| Feature | Package | Graceful Fallback |
|---------|---------|-------------------|
| Rate Limiting | `Flask-Limiter` | Disabled with warning |
| CORS | `Flask-CORS` | Disabled with warning |
| HTML Sanitization | `bleach` | Regex-based fallback |

**Note**: All packages are optional. MyWave functions normally if they're not installed, with security features gracefully degrading.

### Installation

```bash
# Install optional security packages
pip install flask-limiter flask-cors bleach cryptography

# Or install with all security extras
pip install -r requirements.txt
```

---

## 7. Testing

### Unit Tests

Comprehensive unit tests are available in `tests/unit/test_security.py`:

```bash
# Run all security tests
pytest tests/unit/test_security.py -q

# Run specific test class
pytest tests/unit/test_security.py::TestRateLimiting -v

# Run with coverage
pytest tests/unit/test_security.py --cov=app.services.security_service
```

### Test Coverage

- **Rate Limiting**: 7 tests
- **CORS Configuration**: 6 tests
- **Input Validation**: 11 tests
- **Secrets Management**: 10 tests
- **Security Headers**: 2 tests
- **Integration**: 7 tests

**Total**: 43 unit tests, all passing ✅

---

## 8. Best Practices

### 1. Always Validate Input

```python
# ❌ BAD: Trust user input
user_comment = request.form.get('comment')
db.session.add(BlogComment(text=user_comment))

# ✅ GOOD: Validate and sanitize
user_comment = InputValidator.sanitize_html(request.form.get('comment', ''))
if not user_comment:
    return {'error': 'Comment too short'}, 400
db.session.add(BlogComment(text=user_comment))
```

### 2. Protect Sensitive Endpoints

```python
# ❌ BAD: No rate limiting
@app.route('/api/auth/login', methods=['POST'])
def login():
    pass

# ✅ GOOD: Apply rate limiting
@app.route('/api/auth/login', methods=['POST'])
@rate_limited('auth')  # 5 per minute
def login():
    pass
```

### 3. Use Environment Variables for Secrets

```python
# ❌ BAD: Hardcoded secrets
API_KEY = 'my-secret-key-12345'
DB_PASSWORD = 'password123'

# ✅ GOOD: Load from environment
API_KEY = SecretsManager.get_secret('API_KEY')
DB_PASSWORD = SecretsManager.get_secret('DATABASE_PASSWORD')
```

### 4. Hash Passwords Always

```python
# ❌ BAD: Store plain text password
user.password = request.form.get('password')

# ✅ GOOD: Hash password
hashed_pwd, salt = SecretsManager.hash_password(request.form.get('password'))
user.password = hashed_pwd
user.salt = salt
```

### 5. Enable HTTPS in Production

```bash
# In Flask config
PREFERRED_PROTOCOL = 'https'
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
```

### 6. Configure CSP Headers for Your Domains

```python
# In SecurityHeaders
'Content-Security-Policy': 'default-src "self"; script-src "self" https://trusted-cdn.com; ...'
```

---

## 9. Troubleshooting

### Issue: Rate Limiting Not Working

**Symptom**: Requests aren't being limited despite configuration

**Solution**:

```bash
# Check if Flask-Limiter is installed
pip install flask-limiter

# Check RATELIMIT_DISABLED environment variable
echo $RATELIMIT_DISABLED  # Should be empty or 'false'
```

### Issue: CORS Requests Failing

**Symptom**: Browser blocks cross-origin requests with CORS error

**Solution**:

```bash
# Verify CORS_ORIGINS environment variable
echo $CORS_ORIGINS

# Should contain your frontend domain
export CORS_ORIGINS="https://example.com,https://www.example.com"
```

### Issue: HTML Sanitization Not Working

**Symptom**: Dangerous tags not being removed

**Solution**:

```bash
# Install bleach for proper HTML sanitization
pip install bleach

# Verify in logs:
# Should NOT see: "bleach not installed, using regex fallback"
```

### Issue: Secrets Not Accessible

**Symptom**: `SecretsManager.get_secret()` returns None

**Solution**:

```bash
# Set environment variable
export API_KEY="your_32_char_api_key_here"

# Or use default
api_key = SecretsManager.get_secret('API_KEY', default='fallback_value')
```

---

## 10. Security Checklist

Before deploying to production, verify:

- [ ] All rate limits are configured for your endpoints
- [ ] CORS origins are restricted to trusted domains
- [ ] Input validation is applied to all user inputs
- [ ] Passwords are hashed with SecretsManager
- [ ] API keys are validated before processing requests
- [ ] Security headers are enabled (init_security_headers called)
- [ ] HTTPS is enforced (SESSION_COOKIE_SECURE=True)
- [ ] All tests pass (pytest tests/unit/test_security.py)
- [ ] Flask-Limiter is installed for rate limiting
- [ ] Flask-CORS is installed for CORS support
- [ ] bleach is installed for HTML sanitization

---

## 11. References

- [OWASP Top 10](https://owasp.org/Top10/)
- [Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [PBKDF2 Standard](https://en.wikipedia.org/wiki/PBKDF2)
- [Fernet Encryption](https://cryptography.io/en/latest/fernet/)

---

**Last Updated**: 2024
**Security Service Version**: 1.0
**Test Coverage**: 43 tests, 100% pass rate
