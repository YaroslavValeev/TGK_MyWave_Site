"""Capture PR53.2 blog mobile fix evidence (390x844)."""
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:5000"
OUT = Path("docs/evidence/pr532/screenshots")
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True)
        page = ctx.new_page()
        page.route("**/*", lambda route: route.abort() if route.request.resource_type in ("image", "font", "media") else route.continue_())
        page.goto(f"{BASE}/blog", wait_until="commit", timeout=120000)
        page.wait_for_timeout(1200)
        page.screenshot(path=str(OUT / "mobile_390x844_blog_index_after.png"), full_page=True)
        ctx.close()
        browser.close()
    print("saved", OUT / "mobile_390x844_blog_index_after.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
