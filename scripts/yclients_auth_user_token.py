#!/usr/bin/env python3
"""Obtain YCLIENTS User token via partner Bearer + user login/password.

Does NOT print password. Writes token to stdout only.

Usage:
  cd /var/www/mywave && source venv/bin/activate
  set -a; source .env; set +a
  python scripts/yclients_auth_user_token.py --login 'YOU@EMAIL' --password-env YCLIENTS_USER_PASSWORD
"""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--login", required=True)
    parser.add_argument(
        "--password-env",
        default="YCLIENTS_USER_PASSWORD",
        help="Env var name holding the YCLIENTS user password",
    )
    args = parser.parse_args()
    password = os.environ.get(args.password_env, "").strip()
    if not password:
        print(f"ERROR: set {args.password_env}", file=sys.stderr)
        return 1

    from app.services.booking.providers.yclients import (
        YclientsApiError,
        YclientsNotConfiguredError,
        auth_user_token,
    )

    try:
        token = auth_user_token(args.login, password)
    except (YclientsNotConfiguredError, YclientsApiError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(token)
    print(
        "\n# Add to .env (do not commit):\n"
        f"YCLIENTS_USER_TOKEN={token[:6]}…{token[-4:]}  # full token printed above",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
