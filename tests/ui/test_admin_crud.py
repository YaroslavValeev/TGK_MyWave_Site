import pytest
from playwright.sync_api import sync_playwright


@pytest.mark.ui
def test_admin_crud():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        # Логин в админку
        page.goto("http://localhost:5000/admin/login")
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', "adminpass")
        page.click('button[type="submit"]')
        assert "/admin" in page.url
        # Создание пользователя
        page.goto("http://localhost:5000/admin/users/create")
        page.fill('input[name="username"]', "newuser")
        page.fill('input[name="email"]', "newuser@mail.com")
        page.fill('input[name="password"]', "1234")
        page.click('button[type="submit"]')
        assert "newuser" in page.content()
        # Удаление пользователя
        page.goto("http://localhost:5000/admin/users")
        page.click("button.delete-user")
        assert "newuser" not in page.content()
        browser.close()
