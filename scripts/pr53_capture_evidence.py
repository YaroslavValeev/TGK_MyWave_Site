"""Capture PR53 UI evidence screenshots (mobile + desktop).

Requires local Flask on http://127.0.0.1:5000 and Playwright chromium.
Run: python scripts/pr53_capture_evidence.py
"""
from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path("docs/evidence/pr53/screenshots")
OUT.mkdir(parents=True, exist_ok=True)

MOBILE_VIEWPORTS = (
    ("mobile_390x844", {"width": 390, "height": 844}),
    ("mobile_360x800", {"width": 360, "height": 800}),
)
DESKTOP_VIEWPORT = ("desktop_1366x768", {"width": 1366, "height": 768})


def _block_heavy_requests(page):
    def handler(route):
        req = route.request
        if req.resource_type in ("image", "media", "font") or any(
            host in req.url
            for host in (
                "google-analytics",
                "googletagmanager",
                "mc.yandex",
                "facebook",
                "doubleclick",
            )
        ):
            route.abort()
        else:
            route.continue_()

    page.route("**/*", handler)


def _hide_overlays(page):
    page.evaluate(
        """() => {
          document.querySelectorAll('.cookie-banner, #cookieConsent, .chat-widget').forEach(el => {
            el.style.display = 'none';
          });
        }"""
    )


def _open_booking_step1(page):
    page.goto(f"{BASE}/", wait_until="commit", timeout=120000)
    page.wait_for_timeout(800)
    _hide_overlays(page)
    btn = page.locator("#openBookingBtn")
    if btn.count():
        btn.first.click()
        page.wait_for_timeout(600)
    else:
        page.evaluate(
            """() => {
              const m = document.getElementById('modalCalendar');
              if (m) { m.classList.remove('hidden'); m.style.display = 'flex'; }
            }"""
        )


def _open_booking_step2_slots(page):
    page.evaluate(
        """() => {
          ['modalCalendar','modalContact','modalConfirm'].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.classList.add('hidden'); el.style.display = 'none'; }
          });
          const slots = document.getElementById('modalSlots');
          if (!slots) return;
          slots.classList.remove('hidden');
          slots.style.display = 'flex';
          const container = document.getElementById('slotButtonsContainer');
          if (container) {
            container.innerHTML = '';
            ['10:00','11:00','12:00','13:00','14:00','15:00'].forEach(t => {
              const b = document.createElement('button');
              b.className = 'slot-btn available';
              b.textContent = t;
              container.appendChild(b);
            });
          }
          const picker = document.getElementById('boatSetPicker');
          if (picker) { picker.classList.add('hidden'); picker.setAttribute('aria-hidden','true'); }
        }"""
    )
    page.wait_for_timeout(400)


def _open_booking_step2_boat_sets(page):
    page.evaluate(
        """() => {
          const slots = document.getElementById('modalSlots');
          if (slots) { slots.classList.remove('hidden'); slots.style.display = 'flex'; }
          const container = document.getElementById('slotButtonsContainer');
          if (container) {
            container.innerHTML = '';
            const b = document.createElement('button');
            b.className = 'slot-btn available active';
            b.textContent = '10:00–11:00';
            container.appendChild(b);
          }
          const picker = document.getElementById('boatSetPicker');
          const btns = document.getElementById('boatSetButtons');
          if (picker && btns) {
            picker.classList.remove('hidden');
            picker.setAttribute('aria-hidden','false');
            btns.innerHTML = '';
            [1,2,3,4].forEach(n => {
              const btn = document.createElement('button');
              btn.className = 'boat-set-btn' + (n === 2 ? ' active' : '');
              btn.textContent = String(n);
              btns.appendChild(btn);
            });
            const preview = document.getElementById('boatRangePreview');
            if (preview) preview.textContent = '10:00 – 12:00 (2 сета)';
          }
        }"""
    )
    page.wait_for_timeout(400)


def _capture_booking(prefix: str, page):
    _open_booking_step1(page)
    page.screenshot(path=str(OUT / f"{prefix}_01_booking_step1_date.png"), full_page=True)
    _open_booking_step2_slots(page)
    page.screenshot(path=str(OUT / f"{prefix}_02_booking_step2_slots.png"), full_page=True)
    page.screenshot(
        path=str(OUT / f"{prefix}_03_booking_back_button.png"),
        full_page=False,
        clip={"x": 0, "y": 0, "width": page.viewport_size["width"], "height": min(844, page.viewport_size["height"])},
    )
    _open_booking_step2_boat_sets(page)
    page.screenshot(path=str(OUT / f"{prefix}_04_booking_set_count.png"), full_page=True)


def _capture_product(prefix: str, page):
    page.goto(f"{BASE}/shop/product/balance-board", wait_until="commit", timeout=120000)
    page.wait_for_timeout(800)
    _hide_overlays(page)
    page.screenshot(path=str(OUT / f"{prefix}_05_product_card.png"), full_page=True)

    buy = page.locator("[data-product-request]").first
    if buy.count():
        buy.click()
        page.wait_for_timeout(500)
    page.screenshot(path=str(OUT / f"{prefix}_06_product_modal_empty.png"), full_page=True)

    page.fill('#product-request-form input[name="name"]', "Мария Тест")
    page.fill('#product-request-form input[name="phone"]', "+7 916 123 45 67")
    page.fill('#product-request-form input[name="telegram"]', "@maria_test")
    page.fill('#product-request-form input[name="email"]', "maria@example.com")
    page.fill('#product-request-form textarea[name="comment"]', "Нужен самовывоз в выходные")
    page.screenshot(path=str(OUT / f"{prefix}_07_product_modal_filled.png"), full_page=True)

    page.route(
        "**/shop/api/product-request",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body='{"ok":true,"message":"Заявка отправлена. Мы уточним наличие товара и свяжемся с вами для подтверждения заказа."}',
        ),
    )
    page.locator('#product-request-form button[type="submit"]').click()
    page.wait_for_timeout(700)
    page.screenshot(path=str(OUT / f"{prefix}_08_product_success.png"), full_page=True)

    page.unroute("**/shop/api/product-request")
    page.reload(wait_until="commit", timeout=120000)
    page.wait_for_timeout(800)
    _hide_overlays(page)
    page.evaluate(
        """() => {
          const modal = document.getElementById('modalProductRequest');
          const form = document.getElementById('product-request-form');
          if (modal && form) {
            form.querySelector('[name=\"product_id\"]').value = 'balance-board';
            form.querySelector('[name=\"product_title\"]').value = 'Баланс-борд';
            modal.classList.remove('hidden');
            modal.classList.add('show');
            modal.style.display = 'flex';
          }
        }"""
    )
    page.wait_for_timeout(400)
    page.route(
        "**/shop/api/product-request",
        lambda route: route.fulfill(
            status=500,
            content_type="application/json",
            body='{"ok":false,"error":"Не удалось сохранить заявку"}',
        ),
    )
    page.evaluate(
        """() => {
          const modal = document.getElementById('modalProductRequest');
          const form = document.getElementById('product-request-form');
          const msg = document.getElementById('product-request-message');
          if (modal) {
            modal.classList.remove('hidden');
            modal.classList.add('show');
            modal.style.display = 'flex';
          }
          if (form) {
            form.querySelector('[name=\"name\"]').value = 'Test';
            form.querySelector('[name=\"phone\"]').value = '+7 900 000 00 00';
          }
        }"""
    )
    page.locator('#product-request-form button[type="submit"]').click(force=True)
    page.wait_for_timeout(700)
    page.screenshot(path=str(OUT / f"{prefix}_09_product_error.png"), full_page=True)


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright  # noqa: F401
    except ImportError:
        print("Playwright not installed", file=sys.stderr)
        return 1

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        for name, vp in MOBILE_VIEWPORTS:
            ctx = browser.new_context(viewport=vp, device_scale_factor=2, is_mobile=True)
            page = ctx.new_page()
            _block_heavy_requests(page)
            _capture_booking(name, page)
            _capture_product(name, page)
            ctx.close()

        dname, dvp = DESKTOP_VIEWPORT
        ctx = browser.new_context(viewport=dvp)
        page = ctx.new_page()
        _block_heavy_requests(page)
        _open_booking_step1(page)
        page.screenshot(path=str(OUT / f"{dname}_01_booking_step1.png"), full_page=False)
        page.goto(f"{BASE}/shop/product/balance-board", wait_until="commit", timeout=120000)
        page.wait_for_timeout(600)
        page.screenshot(path=str(OUT / f"{dname}_02_product_page.png"), full_page=False)
        ctx.close()
        browser.close()

    files = sorted(OUT.glob("*.png"))
    print(f"Saved {len(files)} screenshots to {OUT.resolve()}")
    for f in files:
        print(f"  - {f.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
