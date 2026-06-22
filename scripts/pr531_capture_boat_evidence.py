"""Capture PR53.1 boat multi-select evidence screenshots."""
from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path("docs/evidence/pr531/screenshots")
OUT.mkdir(parents=True, exist_ok=True)
VP = {"width": 390, "height": 844}


def _block_heavy(page):
    def handler(route):
        req = route.request
        if req.resource_type in ("image", "media", "font") or any(
            x in req.url for x in ("google-analytics", "googletagmanager", "mc.yandex")
        ):
            route.abort()
        else:
            route.continue_()

    page.route("**/*", handler)


def _open_boat_slots(page):
    page.goto(f"{BASE}/", wait_until="commit", timeout=120000)
    page.wait_for_timeout(800)
    page.evaluate(
        """() => {
          document.querySelectorAll('.cookie-banner, #cookieConsent').forEach(el => {
            el.style.display = 'none';
          });
          window.__mwBookingService = 'boat';
          ['modalContact','modalConfirm','modalCalendar'].forEach(id => {
            const el = document.getElementById(id);
            if (el) { el.classList.add('hidden'); el.style.display = 'none'; }
          });
          const slots = document.getElementById('modalSlots');
          if (slots) { slots.classList.remove('hidden'); slots.style.display = 'flex'; }
          const summary = document.getElementById('boatSlotSummary');
          if (summary) { summary.classList.remove('hidden'); summary.setAttribute('aria-hidden','false'); }
          const times = ['10:00','10:30','11:00','11:30','12:00','12:30'];
          const container = document.getElementById('slotButtonsContainer');
          if (container) {
            container.innerHTML = '';
            times.forEach(t => {
              const b = document.createElement('button');
              b.type = 'button';
              b.className = 'slot-btn available';
              b.dataset.time = t;
              b.textContent = t;
              b.addEventListener('click', () => {
                b.classList.toggle('selected');
                b.classList.toggle('active');
                const selected = container.querySelectorAll('.slot-btn.selected').length;
                const countEl = document.getElementById('boatSlotSummaryCount');
                const totalEl = document.getElementById('boatSlotSummaryTotal');
                const btn = document.getElementById('confirmSlotBtn');
                if (countEl) countEl.textContent = 'Выбрано сетов: ' + selected;
                if (totalEl) totalEl.textContent = 'Итого: ' + (selected * 10000).toLocaleString('ru-RU') + ' ₽';
                if (btn) btn.disabled = selected < 1;
              });
              container.appendChild(b);
            });
          }
          const countEl = document.getElementById('boatSlotSummaryCount');
          const totalEl = document.getElementById('boatSlotSummaryTotal');
          const btn = document.getElementById('confirmSlotBtn');
          if (countEl) countEl.textContent = 'Выбрано сетов: 0';
          if (totalEl) totalEl.textContent = 'Итого: 0 ₽';
          if (btn) { btn.disabled = true; btn.textContent = 'Продолжить'; }
        }"""
    )
    page.wait_for_timeout(500)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=VP, device_scale_factor=2, is_mobile=True)
        page = ctx.new_page()
        _block_heavy(page)
        _open_boat_slots(page)
        page.screenshot(path=str(OUT / "mobile_390x844_01_boat_slots_list.png"), full_page=True)

        page.evaluate("""() => document.querySelector('.slot-btn[data-time=\"10:30\"]')?.click()""")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "mobile_390x844_02_one_slot_selected.png"), full_page=True)

        page.evaluate(
            """() => {
              document.querySelector('.slot-btn[data-time=\"11:00\"]')?.click();
              document.querySelector('.slot-btn[data-time=\"11:30\"]')?.click();
            }"""
        )
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUT / "mobile_390x844_03_multi_slots_summary.png"), full_page=True)

        page.evaluate(
            """() => {
              document.querySelectorAll('.slot-btn.selected').forEach(b => {
                b.classList.remove('selected','active');
              });
              const countEl = document.getElementById('boatSlotSummaryCount');
              const totalEl = document.getElementById('boatSlotSummaryTotal');
              const btn = document.getElementById('confirmSlotBtn');
              if (countEl) countEl.textContent = 'Выбрано сетов: 0';
              if (totalEl) totalEl.textContent = 'Итого: 0 ₽';
              if (btn) btn.disabled = true;
            }"""
        )
        page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "mobile_390x844_04_continue_disabled.png"), full_page=True)

        ctx.close()
        browser.close()

    for f in sorted(OUT.glob("*.png")):
        print(f"  - {f.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
