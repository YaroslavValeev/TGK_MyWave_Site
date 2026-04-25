#!/usr/bin/env python3
"""
Проверка persistence чата на стенде / локально.

Выход:
  0 — таблица chat_message есть, при желании видны недавние строки
  1 — ошибка (нет таблицы, нет БД, и т.д.)

Примеры:
  FLASK_CONFIG=production python scripts/chat_persistence_check.py
  python scripts/chat_persistence_check.py --config testing

После деплоя на стенд Owner должен:
  1) Применить миграции: flask db upgrade  (или alembic upgrade head)
  2) Запустить этот скрипт с тем же DATABASE_URL, что у приложения
  3) Отправить сообщение в /chat/api и снова запустить с --expect-rows N
"""
from __future__ import annotations

import argparse
import os
import sys


def main() -> int:
    p = argparse.ArgumentParser(description="Проверка таблицы chat_message")
    p.add_argument(
        "--config",
        default=os.environ.get("FLASK_CONFIG", "development"),
        help="Имя конфига create_app (development, testing, production, ...)",
    )
    p.add_argument(
        "--expect-rows",
        type=int,
        default=0,
        help="Если >0 — после смоука чата ожидаем минимум столько строк в chat_message",
    )
    args = p.parse_args()

    try:
        from app import create_app
        from sqlalchemy import inspect, text

        app = create_app(config_name=args.config)
        with app.app_context():
            from app.database.models import db

            insp = inspect(db.engine)
            tables = insp.get_table_names()
            if "chat_message" not in tables:
                print("FAIL: таблица chat_message отсутствует. Выполните: flask db upgrade")
                return 1
            print("OK: таблица chat_message существует")

            with db.engine.connect() as conn:
                n = conn.execute(text("SELECT COUNT(*) FROM chat_message")).scalar()
            print(f"INFO: строк в chat_message: {n}")

            if args.expect_rows > 0 and (n or 0) < args.expect_rows:
                print(
                    f"FAIL: ожидалось >= {args.expect_rows} строк, фактически {n}. "
                    "Проверьте, что POST /chat/api реально пишет в БД."
                )
                return 1

    except Exception as e:
        print(f"FAIL: {e}")
        return 1

    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
