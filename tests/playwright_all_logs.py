from playwright.sync_api import sync_playwright
import time


def main():
    url = "http://localhost:5000/"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_msgs = []
        page.on("console", lambda msg: console_msgs.append((msg.type, msg.text)))

        # Start recording before page load
        page.goto(url, timeout=20000)  # Wait for full page load, not just DOMContentLoaded
        
        time.sleep(1)

        # Now list ALL console messages to see the sequence
        print("All console messages (chronological order):")
        for i, (msg_type, msg_text) in enumerate(console_msgs):
            print(f"{i:2d}. [{msg_type:5s}] {msg_text[:120]}")

        # Check final status again
        status = page.evaluate("() => window.bookingStatus || 'undefined'")
        print(f"\nFinal window.bookingStatus: {status}")

        browser.close()


if __name__ == "__main__":
    main()
