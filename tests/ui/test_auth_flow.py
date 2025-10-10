import pytest
from playwright.sync_api import sync_playwright

@pytest.mark.ui
def test_registration():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('http://localhost:5000/register')
        page.fill('input[name="username"]', 'testuser')
        page.fill('input[name="email"]', 'testuser@mail.com')
        page.fill('input[name="password"]', 'password123')
        page.click('button[type="submit"]')
        assert page.url.endswith('/dashboard')
        browser.close() 