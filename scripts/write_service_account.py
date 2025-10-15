"""Write a JSON string from an environment variable to a file.

This script reads a JSON value stored in an environment variable and writes
it safely to the given output path. Intended for CI where secrets are
provided as environment variables.

Usage:
  python scripts/write_service_account.py --env-var GOOGLE_SERVICE_ACCOUNT_JSON --out-file instance/service_account.json
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--env-var', required=True, help='Name of environment variable that contains JSON')
    parser.add_argument('--out-file', required=True, help='Path to write the JSON file')
    args = parser.parse_args()

    env_name = args.env_var
    out_path = args.out_file

    value = os.environ.get(env_name)
    if not value:
        print(f"Environment variable {env_name} is empty or not set", file=sys.stderr)
        return 2

    # Ensure directory exists
    dir_name = os.path.dirname(out_path)
    if dir_name and not os.path.exists(dir_name):
        os.makedirs(dir_name, exist_ok=True)

    # Write file atomically
    tmp_path = out_path + '.tmp'
    try:
        with open(tmp_path, 'w', encoding='utf-8') as f:
            f.write(value)
        os.replace(tmp_path, out_path)
    except Exception as exc:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        print(f'Failed to write service account file: {exc}', file=sys.stderr)
        return 3

    print(f'Wrote service account JSON to {out_path}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
"""Write Google service account JSON to the expected file path from environment variable.

This script reads the environment variable GOOGLE_SERVICE_ACCOUNT_JSON (set in CI secrets)
and writes it to the file path that the application expects (config/service_account.json by default).
It is idempotent and safe to run in CI.
"""
import os
import json
from pathlib import Path

SERVICE_ACCOUNT_ENV = "GOOGLE_SERVICE_ACCOUNT_JSON"
OUT_PATH = Path(__file__).resolve().parents[1] / "config" / "service_account.json"


def main():
    raw = os.environ.get(SERVICE_ACCOUNT_ENV)
    if not raw:
        print(f"Environment variable {SERVICE_ACCOUNT_ENV} is not set. Skipping write.")
        return

    try:
        # Try to parse to ensure valid JSON
        parsed = json.loads(raw)
    except Exception as exc:
        print(f"Provided {SERVICE_ACCOUNT_ENV} is not valid JSON: {exc}")
        raise

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(parsed, fh, indent=2, ensure_ascii=False)

    print(f"Wrote service account JSON to {OUT_PATH}")


if __name__ == "__main__":
    main()
