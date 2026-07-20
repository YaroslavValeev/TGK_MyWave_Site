#!/usr/bin/env python3
"""Preflight: Tour Camp API from Site runtime env (same as gunicorn)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except ImportError:
    pass

from app.config.camp_features import (  # noqa: E402
    get_camp_feature_flags,
    mywave_tour_camp_api_token,
    mywave_tour_camps_api_url,
)
from app.services.camps.showcase import fetch_showcase_camps, is_showcase_public  # noqa: E402
from app.services.camps.tour_client import (  # noqa: E402
    TourCampFetchError,
    fetch_tour_camp_detail,
    fetch_tour_camps,
    fetch_tour_camps_page,
)


def _token_fp(token: str) -> str:
    token = token.strip()
    if not token:
        return "missing"
    if len(token) <= 8:
        return "set(len<=8)"
    return f"set(len={len(token)}, tail={token[-4:]})"


def main() -> int:
    flags = get_camp_feature_flags()
    api_url = mywave_tour_camps_api_url()
    token = mywave_tour_camp_api_token()

    print("camp_flags:", flags)
    print("MYWAVE_TOUR_CAMPS_API_URL:", api_url)
    print("MYWAVE_TOUR_CAMP_API_TOKEN:", _token_fp(token))

    if not flags.get("CAMP_MODULE_ENABLED"):
        print("FAIL: CAMP_MODULE_ENABLED=0")
        return 1
    if not token:
        print("FAIL: MYWAVE_TOUR_CAMP_API_TOKEN missing in process env")
        return 1

    try:
        items, next_offset = fetch_tour_camps_page(limit=5)
    except TourCampFetchError as exc:
        print(f"FAIL: list API status={exc.status_code} kind={exc.kind} msg={exc}")
        return 1

    print(f"OK: list items={len(items)} next_offset={next_offset}")
    public = [raw for raw in items if is_showcase_public(raw)]
    print(f"OK: showcase_public={len(public)} of {len(items)}")

    try:
        all_items = fetch_tour_camps()
    except TourCampFetchError as exc:
        print(f"FAIL: paginated list status={exc.status_code} kind={exc.kind} msg={exc}")
        return 1
    print(f"OK: fetch_tour_camps items={len(all_items)}")

    sample_id = "tour_camp_api_mvp_wakesurf_v1"
    try:
        detail = fetch_tour_camp_detail(sample_id)
        print(f"OK: detail id={detail.get('id')} title={detail.get('title')!r}")
    except TourCampFetchError as exc:
        print(f"FAIL: detail status={exc.status_code} kind={exc.kind} msg={exc}")
        return 1
    except ValueError as exc:
        print(f"FAIL: detail shape {exc}")
        return 1

    showcase = fetch_showcase_camps()
    print(f"OK: showcase state={showcase.state} camps={len(showcase.camps)}")
    if showcase.state != "ok":
        print(f"WARN: message={showcase.message}")
        return 1

    out = ROOT / "instance" / "mywave-camps-sample.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    import json

    out.write_text(
        json.dumps({"items": items[:3]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"saved: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
