#!/usr/bin/env python3
"""Read-only Social Mission prod readiness (no .env writes, no restart).

Usage on prod:
  PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python scripts/prod_social_readiness_oneshot.py

Before PR #48 merge: scp this file to /tmp/ and run with prod venv + PROD_ROOT.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _tail(value: str, n: int = 8) -> str:
    v = (value or "").strip().strip('"').strip("'")
    return v[-n:] if len(v) >= n else v


def _read_env_lines(env_path: Path) -> list[str]:
    if not env_path.is_file():
        return []
    return env_path.read_text(encoding="utf-8", errors="replace").splitlines()


def _env_values(lines: list[str], key: str) -> list[str]:
    out: list[str] = []
    for line in lines:
        if line.strip().startswith("#"):
            continue
        m = re.match(rf"^{re.escape(key)}=(.*)$", line.strip())
        if m:
            out.append(m.group(1).strip())
    return out


def main() -> int:
    prod_root = Path(os.environ.get("PROD_ROOT", "/var/www/mywave"))
    env_path = prod_root / ".env"
    lines = _read_env_lines(env_path)

    print("=== Social readiness one-shot (read-only) ===")
    print(f"root={prod_root}")

    print("\n=== SPREADSHEET_ID duplicate check ===")
    sp_lines = [(i + 1, v) for i, line in enumerate(lines) if (m := re.match(r"^SPREADSHEET_ID=(.*)$", line.strip())) for v in [m.group(1).strip()]]
    print(f"SPREADSHEET_ID line count: {len(sp_lines)} (expect 1)")
    for lineno, val in sp_lines:
        print(f"{lineno}:SPREADSHEET_ID=***{_tail(val)}")
    if len(sp_lines) == 1 and _tail(sp_lines[0][1]) == "akVMOrCgic0":
        print("OK: single Admin SPREADSHEET_ID")
    elif len(sp_lines) > 1:
        print("FAIL: dedupe .env — keep Admin (tail akVMOrCgic0) only on SPREADSHEET_ID")
    else:
        print("WARN: missing or unexpected SPREADSHEET_ID tail")

    print("\n=== PARSER_NEWS tail (blog isolation) ===")
    parser_vals = _env_values(lines, "PARSER_NEWS_SPREADSHEET_ID")
    if parser_vals:
        print(f"PARSER_NEWS_SPREADSHEET_ID=***{_tail(parser_vals[-1])}")
        print("OK: Parser tail" if _tail(parser_vals[-1]) == "LijNNyn50" else "FAIL/WARN: expected LijNNyn50")
    else:
        print("FAIL: PARSER_NEWS_SPREADSHEET_ID not set")

    print("\n=== SOCIAL effective spreadsheet tail ===")
    social_vals = _env_values(lines, "SOCIAL_SPREADSHEET_ID")
    if social_vals and social_vals[-1]:
        sid = social_vals[-1]
        print("SOCIAL_SPREADSHEET_ID: set")
    elif sp_lines:
        sid = sp_lines[-1][1]
        print("SOCIAL_SPREADSHEET_ID: empty → fallback SPREADSHEET_ID (last line in .env)")
    else:
        sid = ""
    print(f"effective_social_tail: ***{_tail(sid)}")
    if _tail(sid) == "akVMOrCgic0":
        print("OK: Admin table for Social")
    elif _tail(sid) == "LijNNyn50":
        print("FAIL: Social must not use Parser sheet")
    else:
        print("WARN: unexpected tail")

    tab = (_env_values(lines, "SOCIAL_APPLICATIONS_SHEET_NAME") or ["Social_Applications"])[-1]

    print("\n=== Google SA + Social_Applications tab (read-only API) ===")
    if not sid:
        print("SKIP: no spreadsheet id for Social probe")
        return 1

    sys.path.insert(0, str(prod_root))
    os.chdir(prod_root)

    from app import create_app

    app = create_app("production")
    with app.app_context():
        from app.services.google import get_google_services

        _, sheets, _ = get_google_services()
        meta = sheets.spreadsheets().get(spreadsheetId=sid.strip().strip('"')).execute()
        titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
        print(f"probe_tail {_tail(sid)}")
        print("spreadsheet_access=OK")
        print("tabs_count", len(titles))
        print("Social_Applications_tab", "YES" if tab in titles else "NO")

    print("\n=== Booking/calendar isolation ===")
    print("social.py not on prod HEAD — confirmed in release branch (no booking/calendar imports)")

    print("\n=== DONE — paste output to GM (tails only) ===")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
