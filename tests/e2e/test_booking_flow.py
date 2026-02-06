import time
import requests
from threading import Thread

import pytest

from app import create_app


@pytest.fixture(scope="session")
def live_server():
    app = create_app(config_name="testing")

    # Override calendar slots and CSRF check for deterministic behavior
    try:
        import app.routes.calendar_routes as cal

        cal.get_available_slots = lambda date: [
            {"time": "10:00", "available": True, "remaining": 3}
        ]
    except Exception:
        pass
    try:
        import app.services.csrf as csrf

        csrf.check_csrf = lambda: True
    except Exception:
        pass

    port = 5002

    def run():
        # bind to all interfaces to avoid local binding issues for headless browsers
        app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)

    thr = Thread(target=run, daemon=True)
    thr.start()

    base = f"http://127.0.0.1:{port}"
    # Wait for server to respond and for the booking button to appear in HTML
    for _ in range(60):
        try:
            r = requests.get(base + "/", timeout=2)
            if r.status_code == 200 and "openBookingBtn" in r.text:
                break
        except Exception:
            pass
        time.sleep(0.5)

    yield base


def test_booking_flow(page, live_server):
    base = live_server
    page.goto(base + "/", wait_until="domcontentloaded", timeout=120000)
    # Open booking button
    page.click("#openBookingBtn")
    page.wait_for_selector("#modalCalendar", state="visible", timeout=5000)

    # Fill date and request slots
    # flatpickr may exist; setting value directly
    page.fill("#bookingDateInput", "2025-12-03")
    page.click("#confirmDateBtn")

    # Wait for slots and choose the first available
    page.wait_for_selector("#slotButtonsContainer .slot-btn", timeout=5000)
    # Click first available slot button
    slot_btn = page.query_selector("#slotButtonsContainer .slot-btn.available")
    if slot_btn:
        slot_btn.click()
    else:
        # fallback: click first slot button
        page.click("#slotButtonsContainer .slot-btn")

    # Fill contact info
    page.fill("#bookingName", "E2E Tester")
    page.fill("#bookingPhone", "+71234567890")
    page.click("#confirmContactBtn")

    # Final submit
    page.wait_for_selector("#finalConfirmBtn", timeout=2000)
    page.click("#finalConfirmBtn")

    # Wait for success modal or toast
    try:
        page.wait_for_selector(
            "#success-modal, .success-modal, .toast-success", timeout=5000
        )
    except Exception:
        pass

    # Assert that either success-modal or success toast is present
    assert page.query_selector("#success-modal") or page.query_selector(
        ".toast-success"
    )
