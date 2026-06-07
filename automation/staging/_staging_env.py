"""Load staging .env with override; guard against prod Sheet/Calendar mix-ups."""

from __future__ import annotations

import os
import sys

STAGING_ROOT = os.environ.get("STAGING_ROOT", "/var/www/mywave-staging")

# Canonical staging IDs (GM contract)
STAGING_SPREADSHEET_ID_DEFAULT = "16Ewm8Npv3bkNH37X-KAm3PWmRedQ1a8xoiO6LPggyBI"
PROD_SPREADSHEET_ID_BLOCKLIST = frozenset(
    {
        "1kyNQVjeLLe4Ra6oWuf84fHqSjUlWXI8MakVMOrCgic0",
    }
)


def _parse_dotenv_last_wins(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if not os.path.isfile(path):
        raise FileNotFoundError(f"staging .env not found: {path}")
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            values[key] = val
    return values


def load_staging_dotenv() -> dict[str, str]:
    """
    Force staging .env into os.environ (last key wins for duplicates).
    Must run before ``from app import create_app``.
    """
    env_path = os.path.join(STAGING_ROOT, ".env")
    parsed = _parse_dotenv_last_wins(env_path)
    for key, val in parsed.items():
        os.environ[key] = val

    sa = os.path.join(STAGING_ROOT, "instance", "service_account.json")
    if os.path.isfile(sa):
        os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = sa
        os.environ.setdefault("GOOGLE_SHEETS_CREDENTIALS", sa)

    return parsed


def expected_staging_spreadsheet_id() -> str:
    return (
        os.environ.get("STAGING_SPREADSHEET_ID")
        or os.environ.get("SPREADSHEET_ID")
        or STAGING_SPREADSHEET_ID_DEFAULT
    ).strip()


def assert_staging_spreadsheet(spreadsheet_id: str, *, script: str) -> None:
    sid = (spreadsheet_id or "").strip()
    expected = expected_staging_spreadsheet_id()
    print(f"{script}_spreadsheet_id", sid)
    print(f"{script}_expected_spreadsheet_id", expected)

    if sid in PROD_SPREADSHEET_ID_BLOCKLIST:
        print(f"{script}_fail prod_spreadsheet_blocklisted", sid)
        raise SystemExit(2)
    if sid != expected:
        print(f"{script}_fail wrong_spreadsheet_id", sid, "expected", expected)
        raise SystemExit(2)
    if sid != STAGING_SPREADSHEET_ID_DEFAULT:
        print(f"{script}_warn spreadsheet_id differs from canonical staging default")
