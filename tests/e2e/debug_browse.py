from playwright.sync_api import sync_playwright
import sys
import time

URL = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:5002/'
OUT_SCREEN = 'tests/e2e/debug_screenshot.png'


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()

        def on_console(msg):
            try:
                print('[console]', msg.type, msg.text)
            except Exception:
                pass

        page.on('console', on_console)

        print('Navigating to', URL)
        page.goto(URL, timeout=120000)
        # wait a bit for client-side scripts
        time.sleep(2)
        print('Saving screenshot to', OUT_SCREEN)
        page.screenshot(path=OUT_SCREEN, full_page=True)
        html = page.content()
        print('Page HTML size:', len(html))
        print('First 1000 chars of HTML:\n')
        print(html[:1000])

        browser.close()


if __name__ == '__main__':
    main()
