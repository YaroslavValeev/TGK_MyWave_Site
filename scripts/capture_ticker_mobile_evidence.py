#!/usr/bin/env python3
"""Capture mobile ticker autoplay evidence (390x844 webm). Requires playwright."""

from __future__ import annotations

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT_DIR = ROOT / "docs" / "evidence" / "pr534_1"
OUT_DIR.mkdir(parents=True, exist_ok=True)

FAKE_TICKER = [
    {
        "id": "ev1",
        "label": "Wakesurf · Evidence Cup · Orlando, USA · 01.08–03.08.2026",
        "href": "https://example.com",
        "is_live": False,
    },
    {
        "id": "ev2",
        "label": "Wakeboard · Demo Open · Berlin, DE · 12.09–14.09.2026",
        "href": "https://example.org",
        "is_live": True,
    },
]


def _start_app(port: int = 5019):
    os.environ["ENABLE_GOOGLE_SERVICES"] = "0"
    from app import create_app

    app = create_app(config_name="testing")

    def run():
        app.run(host="127.0.0.1", port=port, threaded=True, use_reloader=False)

    thread = threading.Thread(target=run, daemon=True)
    thread.start()
    time.sleep(4)
    return f"http://127.0.0.1:{port}"


def main() -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed", file=sys.stderr)
        return 1

    base = _start_app()
    video_path = OUT_DIR / "ticker-mobile-390x844.webm"

    with patch("app.services.competitions.store.get_ticker_items", return_value=FAKE_TICKER), patch(
        "app.services.blog.store.get_posts", return_value=([], 0)
    ), sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 390, "height": 844},
            record_video_dir=str(OUT_DIR),
            record_video_size={"width": 390, "height": 844},
        )
        page = context.new_page()
        page.goto(base + "/", wait_until="domcontentloaded", timeout=60000)
        page.locator(".home-competitions-ticker").scroll_into_view_if_needed()
        page.wait_for_timeout(12000)
        page.close()
        context.close()
        browser.close()

    # Playwright names video arbitrarily; rename latest webm
    webms = sorted(OUT_DIR.glob("*.webm"), key=lambda p: p.stat().st_mtime)
    if webms:
        latest = webms[-1]
        if latest != video_path:
            latest.replace(video_path)
        print(f"Saved: {video_path}")
        return 0

    print("No video captured", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
