from playwright.sync_api import sync_playwright
import time


def main():
    url = "http://localhost:5000/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        requests = []
        responses = []
        page.on("request", lambda req: requests.append((req.method, req.url)))
        page.on("response", lambda res: responses.append((res.status, res.url)))

        page.goto(url, wait_until='domcontentloaded', timeout=20000)
        time.sleep(0.5)

        # Check if booking.js was loaded
        booking_js_requests = [r for r in requests if 'booking.js' in r[1]]
        booking_js_responses = [(st, u) for st, u in responses if 'booking.js' in u]

        print("Requests for booking.js:", booking_js_requests)
        print("Responses for booking.js:", booking_js_responses)

        # Check ALL script requests/responses
        script_requests = [r for r in requests if r[1].endswith('.js')]
        script_responses = [(st, u) for st, u in responses if u.endswith('.js')]
        
        print("\nAll .js requests:", len(script_requests))
        for method, url in script_requests[-5:]:  # last 5
            print(f"  {method} {url}")
        
        print("\nAll .js responses (non-200):")
        for status, url in script_responses:
            if status != 200:
                print(f"  {status} {url}")

        browser.close()


if __name__ == "__main__":
    main()
