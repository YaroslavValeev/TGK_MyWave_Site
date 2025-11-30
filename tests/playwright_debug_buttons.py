from playwright.sync_api import sync_playwright
import time


def main():
    url = "http://localhost:5000/"
    print(f"Test: navigating to {url}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        console_msgs = []
        page.on("console", lambda msg: console_msgs.append((msg.type, msg.text)))

        page.goto(url, wait_until='domcontentloaded', timeout=20000)
        time.sleep(0.5)

        # After page load, check what is in UI.openBookingButtons
        result = page.evaluate("""
        () => {
            const logs = {
                querySelectorAll_result: [],
                button_ids: [],
                click_listeners_attached: 0
            };
            
            // Check what querySelectorAll returns
            const btns = document.querySelectorAll("#openBookingBtn, .book-now, .btn-book");
            logs.querySelectorAll_result = Array.from(btns).map(b => ({
                id: b.id,
                class: b.className,
                href: b.getAttribute('href'),
                dataService: b.getAttribute('data-service'),
                hasListener: !!b._clickListener
            }));
            
            // Check all [booking.js] logs from console
            return logs;
        }
        """)
        
        print("Result from page evaluation:")
        print(result)
        
        # Print all console messages to see if there are any errors during init
        print("\nConsole messages (all):")
        for msg_type, msg_text in console_msgs:
            print(f"  {msg_type}: {msg_text[:150]}")

        browser.close()


if __name__ == "__main__":
    main()
