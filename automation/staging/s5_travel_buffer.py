#!/usr/bin/env python3
"""S5 wrapper — runs s5_api_smoke in isolated subprocess (legacy entrypoint)."""

from __future__ import annotations

import os
import subprocess
import sys

STAGING_DIR = os.path.dirname(os.path.abspath(__file__))


def main() -> int:
    proc = subprocess.run(
        [sys.executable, os.path.join(STAGING_DIR, "s5_api_smoke.py")],
        env=os.environ.copy(),
    )
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
