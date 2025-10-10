import pytest
from playwright.sync_api import sync_playwright

@pytest.mark.ui
def test_booking():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto('http://localhost:5000/booking')
        page.fill('input[name="name"]', 'Иван')
        page.fill('input[name="phone"]', '+79991234567')
        page.fill('input[name="date"]', '2024-07-01')
        page.fill('input[name="time"]', '10:00')
        page.click('button[type="submit"]')
        assert 'Спасибо' in page.content() or 'успешно' in page.content().lower()
        browser.close() 