from playwright.sync_api import sync_playwright
import os

HOST = os.environ.get('HOST', 'http://127.0.0.1:5001')
OUT = os.path.join(os.getcwd(), 'artifacts')
os.makedirs(OUT, exist_ok=True)

pages = [('/', 'index'), ('/shop', 'shop'), ('/projects', 'projects')]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={'width': 1280, 'height': 900})
    for path, name in pages:
        page = context.new_page()
        console_messages = []
        def on_console(msg):
            console_messages.append({'type': msg.type, 'text': msg.text})
        page.on('console', on_console)

        page.goto(HOST + path, wait_until='networkidle')
        # full page screenshot
        page.screenshot(path=os.path.join(OUT, f'{name}_full.png'), full_page=True)
        # capture DOM screenshot of projects/store block if exists
        try:
            if name == 'index':
                elem = page.query_selector('#store') or page.query_selector('#projects')
            elif name == 'shop':
                elem = page.query_selector('#shop')
            else:
                elem = page.query_selector('.projects-grid') or page.query_selector('#projects')
            if elem:
                elem.screenshot(path=os.path.join(OUT, f'{name}_block.png'))
        except Exception as e:
            print('Block screenshot failed', e)

        # Capture network image requests
        requests = [r for r in page.context.request._requests.values()] if hasattr(page.context.request, '_requests') else []
        # Save console to file
        with open(os.path.join(OUT, f'{name}_console.txt'), 'w', encoding='utf-8') as f:
            for m in console_messages:
                f.write(f"[{m['type']}] {m['text']}\n")
        # Also save screenshot of network images via DOM: open devtools not available; instead capture image URLs from DOM
        imgs = page.query_selector_all('img')
        img_urls = [img.get_attribute('src') for img in imgs]
        with open(os.path.join(OUT, f'{name}_images.txt'), 'w', encoding='utf-8') as f:
            for u in img_urls:
                f.write(u + '\n')
        page.close()
    context.close()
    browser.close()
    print('Screenshots saved to', OUT)
