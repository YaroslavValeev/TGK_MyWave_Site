#!/usr/bin/env python3
"""Fast smoke: import Flask app, print Online Coaching routes, exit.

No dev server, no Google init when disabled.

Usage:
  DISABLE_TELEGRAM=1 ENABLE_GOOGLE_SERVICES=0 python scripts/smoke_online_coaching_routes.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

PROD_ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    os.environ.setdefault("DISABLE_TELEGRAM", "1")
    os.environ.setdefault("ENABLE_GOOGLE_SERVICES", "0")
    os.environ.setdefault("ONLINE_COACHING_ENABLED", "1")
    sys.path.insert(0, str(PROD_ROOT))
    os.chdir(PROD_ROOT)

    from app import create_app

    app = create_app(os.environ.get("FLASK_CONFIG", "development"))
    rules = sorted(
        r.rule for r in app.url_map.iter_rules() if "online-coaching" in r.rule or "online_coaching" in (r.endpoint or "")
    )
    if not rules:
        print("FAIL: no online coaching routes in url_map")
        return 1

    print("OK online_coaching_routes:")
    for rule in rules:
        print(f"  {rule}")
    print(f"count={len(rules)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
