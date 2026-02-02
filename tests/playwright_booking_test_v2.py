from playwright.sync_api import sync_playwright, TimeoutError
import time


def main():
    url = "http://localhost:5000/"
    print(f"Playwright test: navigating to {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        console_msgs = []
        requests = []
        responses = []

        # Capture all console messages (including error)
        page.on("console", lambda msg: console_msgs.append((msg.type, msg.text)))
        page.on("request", lambda req: requests.append((req.method, req.url)))
        page.on("response", lambda res: responses.append((res.status, res.url)))

        try:
            page.goto(url, wait_until="domcontentloaded", timeout=20000)
        except Exception as e:
            print("First navigation attempt failed (domcontentloaded):", e)
            try:
                page.goto(url, timeout=15000)
            except Exception as e2:
                print("Second navigation attempt failed:", e2)
                browser.close()
                return

        time.sleep(0.5)

        # Try to find a booking button
        selector = "#openBookingBtn"
        btn = page.query_selector(selector)
        if not btn:
            print(f"No booking button found for selector: {selector}")
        else:
            outer = btn.evaluate("el => el.outerHTML")
            print("Found booking element — outerHTML:", outer[:80])

            # Check if _clickListener exists right now
            has_listener = page.evaluate(
                f"() => {{ const el = document.querySelector('{selector}'); return !!el._clickListener; }}"
            )
            print(f"Does button have _clickListener property right now? {has_listener}")

            # Check if button has any click event listeners (via event delegation check)
            listeners_count = page.evaluate(
                f"() => {{ const el = document.querySelector('{selector}'); return el.getEventListeners ? el.getEventListeners('click').length : 'getEventListeners not available'; }}"
            )
            print(f"Click event listeners count: {listeners_count}")

            print("Clicking the element...")
            btn.click()

            # Collect console messages that appeared after click (especially booking.js logs)
            time.sleep(300)  # Brief pause for async events

            # After click, check if the booking logs appeared
            booking_logs = [m for m in console_msgs if "[booking.js]" in m[1]]
            print(f"\nBooking.js console messages (after click): {len(booking_logs)}")
            for msg_type, msg_text in booking_logs:
                print(f"  {msg_type}: {msg_text[:100]}")

            # Check modal state
            modal = page.query_selector("#modalCalendar")
            if modal:
                class_name = modal.get_attribute("class")
                visible = page.evaluate(
                    "el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)",
                    modal,
                )
                print(f'\n#modalCalendar: class="{class_name}"; visible={visible}')
            else:
                print("\n#modalCalendar element not found in DOM.")

        # Full console output
        time.sleep(1)
        print("\n--- All Console Messages ---")
        for msg_type, msg_text in console_msgs:
            if "[booking.js]" in msg_text or msg_type == "error":
                print(f"{msg_type}: {msg_text}")

        print("\n--- Network API Requests ---")
        for method, u in requests:
            if "/api" in u:
                print(f"{method} {u}")

        browser.close()


if __name__ == "__main__":
    main()
