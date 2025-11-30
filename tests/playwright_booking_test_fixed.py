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

        page.on("console", lambda msg: console_msgs.append(f"{msg.type}: {msg.text}"))
        page.on("request", lambda req: requests.append((req.method, req.url)))
        page.on("response", lambda res: responses.append((res.status, res.url)))

        try:
            # prefer domcontentloaded so long-loading external resources don't block the test
            page.goto(url, wait_until='domcontentloaded', timeout=20000)
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
        selector = "a.btn-book, button.btn-book, #openBookingBtn"
        btn = page.query_selector(selector)
        if not btn:
            print(f"No booking button found for selector: {selector}")
            # print some helpful diagnostics
            all_buttons = page.query_selector_all("a, button")
            print(f"Total <a> and <button> elements on page: {len(all_buttons)}")
        else:
            outer = btn.evaluate("el => el.outerHTML")
            print("Found booking element — outerHTML:\n", outer)
            print("Clicking the element...")
            # try both high-level click and a raw DOM click via evaluate
            try:
                btn.click()
            except Exception:
                pass
            try:
                page.evaluate("(sel) => document.querySelector(sel) && document.querySelector(sel).click()", selector)
            except Exception:
                pass

            # After click, inspect modal element state
            page.wait_for_timeout(200)
            modal = page.query_selector("#modalCalendar")
            if modal:
                class_name = modal.get_attribute("class")
                visible = page.evaluate("el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)", modal)
                print(f"#modalCalendar found; class=\"{class_name}\"; visible={visible}")
            else:
                print("#modalCalendar element not found in DOM.")
            # also wait briefly for any .modal.show
            try:
                page.wait_for_selector(".modal.show", timeout=2000)
                print("Found element with .modal.show (modal likely visible).")
            except TimeoutError:
                print("No element with .modal.show detected after click.")

            # If modal did not become visible, attempt direct invocation of stored click handler
            try:
                invoked = page.evaluate("(sel) => { const el = document.querySelector(sel); if (!el) return 'no-el'; if (el._clickListener) { try { el._clickListener(new MouseEvent('click', {bubbles:true, cancelable:true})); return 'invoked-listener'; } catch(e) { return 'listener-failed:' + e.message; } } return 'no-listener'; }", selector)
                print('Direct listener invocation result:', invoked)
                page.wait_for_timeout(200)
                modal = page.query_selector("#modalCalendar")
                if modal:
                    class_name = modal.get_attribute("class")
                    visible = page.evaluate("el => !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length)", modal)
                    print(f"After direct invocation -> #modalCalendar class=\"{class_name}\"; visible={visible}")
                else:
                    print('After direct invocation -> #modalCalendar not found')
            except Exception as e:
                print('Error invoking stored click handler:', e)

        # Short pause to collect network/console
        time.sleep(1)

        print("\n--- Console Messages ---")
        if console_msgs:
            for m in console_msgs:
                print(m)
        else:
            print("(no console messages captured)")

        print("\n--- Network Requests (filtered for /api) ---")
        found_api = False
        for method, u in requests:
            if "/api" in u:
                print(method, u)
                found_api = True
        if not found_api:
            print("(no /api requests captured)")

        print("\n--- Network Responses (filtered for /api) ---")
        found_api_resp = False
        for status, u in responses:
            if "/api" in u:
                print(status, u)
                found_api_resp = True
        if not found_api_resp:
            print("(no /api responses captured)")

        browser.close()


if __name__ == "__main__":
    main()
