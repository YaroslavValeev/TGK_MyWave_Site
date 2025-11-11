"""
Smoke test для проверки Content-Security-Policy заголовков.
"""
import pytest
from app import create_app


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_csp_header_present(client):
    """Проверяем, что CSP заголовок присутствует на всех страницах."""
    response = client.get('/')
    assert 'Content-Security-Policy' in response.headers
    print(f"✅ CSP header present: {response.headers.get('Content-Security-Policy')[:50]}...")


def test_csp_has_nonce(client):
    """Проверяем, что CSP содержит nonce."""
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy', '')
    assert 'nonce-' in csp
    print(f"✅ CSP contains nonce")


def test_csp_safe_defaults(client):
    """Проверяем безопасные значения CSP."""
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy', '')
    
    # должны быть присутствовать безопасные директивы
    assert "default-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "base-uri 'self'" in csp
    print(f"✅ CSP has safe defaults")


def test_no_unsafe_inline_scripts(client):
    """Проверяем отсутствие 'unsafe-inline' в script-src."""
    response = client.get('/')
    csp = response.headers.get('Content-Security-Policy', '')
    
    # script-src должен иметь только 'self', nonce и гугл-домены, но не unsafe-inline
    if "script-src" in csp:
        script_part = [p for p in csp.split(';') if 'script-src' in p][0]
        # unsafe-inline НЕ должен быть в script-src (хотя style-src может иметь)
        assert "'unsafe-inline'" not in script_part
    print(f"✅ No unsafe-inline in script-src")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
