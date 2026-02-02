import time
import requests
from threading import Thread

import pytest

from app import create_app


@pytest.fixture(scope="session")
def live_server():
    app = create_app(config_name="testing")
    port = 5003

    def run():
        # bind to all interfaces to avoid local binding issues for headless browsers
        app.run(host="0.0.0.0", port=port, threaded=True, use_reloader=False)

    thr = Thread(target=run, daemon=True)
    thr.start()

    base = f"http://127.0.0.1:{port}"
    # Wait for server to respond and for the product list to be present in HTML
    for _ in range(60):
        try:
            r = requests.get(base + "/shop/", timeout=2)
            if r.status_code == 200 and "store-products" in r.text:
                break
        except Exception:
            pass
        time.sleep(0.5)

    yield base


def is_visible(element_handle):
    if not element_handle:
        return False
    return element_handle.is_visible()


def test_shop_filter(page, live_server):
    base = live_server
    page.goto(base + "/shop/", wait_until="domcontentloaded", timeout=120000)
    page.wait_for_selector(".filter-btn", timeout=30000)

    # Click 'Пончо' filter
    page.click('.filter-btn[data-category="poncho"]')
    time.sleep(0.5)

    # Ensure at least one product-card with data-category poncho is visible
    cards = page.query_selector_all("#store-products .product-card")
    visible_poncho = False
    for c in cards:
        cat = c.get_attribute("data-category")
        if cat == "poncho" and c.is_visible():
            visible_poncho = True
            break

    assert visible_poncho
