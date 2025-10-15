"""
Write GOOGLE_SERVICE_ACCOUNT_JSON env into a file path readable by the app.
Supports --dry-run to only show what would be written.

Usage:
  python scripts/write_service_account_from_env.py [--out <path>] [--dry-run]

If --out is not provided the script will use environment variable
`GOOGLE_SERVICE_ACCOUNT_FILE` or default to ./service_account.json in the repo root.
This script is intended for CI: set a secret `GOOGLE_SERVICE_ACCOUNT_JSON` and
call this script before running tests.
"""
from __future__ import annotations
import os
import sys
import argparse
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TARGET = REPO_ROOT / 'service_account.json'


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', '-o', help='Output path for service account JSON')
    parser.add_argument('--dry-run', action='store_true', help='Print actions but do not write file')
    args = parser.parse_args(argv)

    json_content = os.environ.get('GOOGLE_SERVICE_ACCOUNT_JSON')
    if not json_content:
        print('Environment variable GOOGLE_SERVICE_ACCOUNT_JSON is not set.')
        return 2

    target = Path(args.out) if args.out else Path(os.environ.get('GOOGLE_SERVICE_ACCOUNT_FILE') or DEFAULT_TARGET)
    target = target.resolve()

    print('Target path for service account file:', str(target))
    if args.dry_run:
        # Only show size and first/last 60 chars for verification
        summary = json_content.strip()
        print('DRY RUN: would write JSON content of length', len(summary))
        sample_head = summary[:60].replace('\n', '')
        sample_tail = summary[-60:].replace('\n', '')
        print('DRY RUN: head:', sample_head)
        print('DRY RUN: tail:', sample_tail)
        return 0

    # Ensure parent exists
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        # Write file safely; on Windows there is no os.chmod reliable behavior for restrictive modes,
        # but we attempt to set owner-only on *nix.
        with open(target, 'w', encoding='utf-8') as f:
            f.write(json_content)
        try:
            # try to set restrictive permissions on POSIX
            os.chmod(target, 0o600)
        except Exception:
            pass
        print('Wrote service account file to', str(target))
        return 0
    except Exception as e:
        print('Failed to write file:', e)
        return 3


if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
