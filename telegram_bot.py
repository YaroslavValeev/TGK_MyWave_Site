#!/usr/bin/env python3
"""
Точка входа для отдельного процесса Telegram (systemd / docker).
Запуск: python telegram_bot.py
Требуется: TG_CONTROL_BOT_TOKEN (см. automation/tg_control_bot.py).
"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    load_dotenv = None  # type: ignore

_root = Path(__file__).resolve().parent


def main() -> None:
    if load_dotenv:
        load_dotenv(_root / ".env")
    sys.path.insert(0, str(_root / "automation"))
    from tg_control_bot import main as run_bot  # noqa: WPS433 — runtime import после PATH

    run_bot()


if __name__ == "__main__":
    main()
