"""Load production .env for read-only automation (no staging guards)."""

from __future__ import annotations

import os


def _parse_dotenv_last_wins(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    if not os.path.isfile(path):
        raise FileNotFoundError(f".env not found: {path}")
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip().strip('"').strip("'")
    return values


def load_prod_dotenv(prod_root: str | None = None) -> dict[str, str]:
    root = (prod_root or os.environ.get("PROD_ROOT") or "/var/www/mywave").rstrip("/")
    env_path = os.path.join(root, ".env")
    parsed = _parse_dotenv_last_wins(env_path)
    for key, val in parsed.items():
        os.environ[key] = val

    for rel in (
        "instance/service_account.json",
        "config/service_account.json",
    ):
        sa = os.path.join(root, rel)
        if os.path.isfile(sa):
            os.environ["GOOGLE_SERVICE_ACCOUNT_FILE"] = sa
            os.environ.setdefault("GOOGLE_SHEETS_CREDENTIALS", sa)
            break

    return parsed
