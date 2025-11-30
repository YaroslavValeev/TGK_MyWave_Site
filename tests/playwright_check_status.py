from playwright.sync_api import sync_playwright
import time
import json


def main():
    url = "http://localhost:5000/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(url, wait_until='domcontentloaded', timeout=20000)
        time.sleep(0.5)

        # Check window.bookingStatus
        status = page.evaluate("() => window.bookingStatus || 'undefined'")
        print("window.bookingStatus:", json.dumps(status, indent=2, ensure_ascii=False))
        
        # Check if DOMContentLoaded fired
        dom_ready = page.evaluate("() => document.readyState")
        print(f"document.readyState: {dom_ready}")
        
        # Check if UI elements exist
        ui_check = page.evaluate("""
        () => ({
            calendarModal: !!document.getElementById("modalCalendar"),
            bookingDateInput: !!document.getElementById("bookingDateInput"),
            openBookingButtons: document.querySelectorAll("#openBookingBtn, .book-now, .btn-book").length,
            hasListener: !!document.querySelector("#openBookingBtn")._clickListener
        })
        """)
        print(f"UI check: {ui_check}")

        browser.close()


if __name__ == "__main__":
    main()
