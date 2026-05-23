#!/usr/bin/env python3
"""Создаёт chat_message на prod, если миграции застряли. Безопасно повторять."""
from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def main() -> int:
    try:
        from app import create_app
        from sqlalchemy import inspect, text

        config_name = os.environ.get("FLASK_CONFIG", "production")
        app = create_app(config_name=config_name)
        with app.app_context():
            from app.database.models import db

            insp = inspect(db.engine)
            if "chat_message" in insp.get_table_names():
                print("OK: chat_message уже существует")
                return 0

            ddl = """
            CREATE TABLE chat_message (
                id INTEGER NOT NULL PRIMARY KEY,
                user VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                created_at DATETIME,
                blog_post_id INTEGER
            )
            """
            with db.engine.begin() as conn:
                conn.execute(text(ddl))
            print("OK: chat_message создана")
            return 0
    except Exception as exc:
        print(f"FAIL: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
