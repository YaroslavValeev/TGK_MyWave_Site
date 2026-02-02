import pytest
from playwright.sync_api import Page, expect


def test_booking_button_opens_modal(page: Page):
    page.goto("http://localhost:5000/")
    # Кликаем по первой кнопке 'Записаться'
    page.click("text=Записаться")
    # Проверяем, что модалка появилась
    modal = page.locator("#modalCalendar")
    expect(modal).to_be_visible()
