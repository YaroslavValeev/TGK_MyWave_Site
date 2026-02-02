from playwright.sync_api import sync_playwright
import time


def main():
    url = "http://localhost:5000/static/js/booking.js"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        response = page.goto(url)
        print(f"Status: {response.status}")
        print("Headers:")
        for key, value in response.all_headers().items():
            print(f"  {key}: {value}")

        # Get response body size
        content = response.body()
        print(f"\nResponse body size: {len(content)} bytes")
        print("First 200 chars of body:")
        print(content[:200].decode("utf-8", errors="ignore"))

        browser.close()


if __name__ == "__main__":
    main()
