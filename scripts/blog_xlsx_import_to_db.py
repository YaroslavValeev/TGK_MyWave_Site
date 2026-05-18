#!/usr/bin/env python3
"""
Импорт publishable-строк блога из XLSX (MyWave_Parser_News, лист raw_feed) в SQLite.

Используйте, когда на проде Sheets пустой/не синхронизирован, а в XLSX есть PUBLISHED/READY_TO_PUBLISH.
Витрина: Sheets first → при 0 постов fallback на БД (app/services/blog/store.py).

Пример (на сервере):
  cd /var/www/mywave && source venv/bin/activate
  python scripts/blog_xlsx_import_to_db.py \\
    --xlsx /tmp/MyWave_Parser_News.xlsx --sheet raw_feed
  curl -sS 'https://mywavewake.ru/api/blog/posts?limit=3'
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.blog_xlsx_dry_run_importer import load_raw_feed_records_from_xlsx
from app.services.blog.publishability import is_publishable_row

COLUMNS_TO_ADD = [
    ("source_type", "VARCHAR(64)"),
    ("source_name", "VARCHAR(128)"),
    ("source_url", "TEXT"),
    ("excerpt", "TEXT"),
    ("content_md", "TEXT"),
    ("content_html", "TEXT"),
    ("content", "TEXT"),
    ("teaser", "VARCHAR(500)"),
    ("cover_image_url", "TEXT"),
    ("tags_json", "TEXT"),
    ("lang", "VARCHAR(16)"),
    ("checksum", "VARCHAR(128)"),
    ("status", "VARCHAR(64)"),
    ("sheet_row_number", "INTEGER"),
    ("published_at", "DATETIME"),
    ("created_at", "DATETIME"),
    ("updated_at", "DATETIME"),
    ("image_id", "INTEGER"),
]


def _ensure_blog_post_schema(db) -> None:
    """Добавляет недостающие колонки blog_post (как flask migrate-blog)."""
    from sqlalchemy import text

    conn = db.engine.connect()
    try:
        result = conn.execute(text("PRAGMA table_info(blog_post)"))
        existing = {row[1] for row in result.fetchall()}
    except Exception:
        db.create_all()
        conn.close()
        return

    if not existing:
        db.create_all()
        conn.close()
        return

    for col_name, col_type in COLUMNS_TO_ADD:
        if col_name not in existing:
            conn.execute(text(f"ALTER TABLE blog_post ADD COLUMN {col_name} {col_type}"))
            conn.commit()
    conn.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Import publishable blog rows from XLSX to SQLite")
    parser.add_argument("--xlsx", required=True, help="Path to MyWave_Parser_News.xlsx")
    parser.add_argument("--sheet", default="raw_feed", help="Worksheet name (default: raw_feed)")
    parser.add_argument("--dry-run", action="store_true", help="Only count rows, no DB write")
    args = parser.parse_args()

    xlsx_path = Path(args.xlsx).expanduser().resolve()
    records, schema = load_raw_feed_records_from_xlsx(xlsx_path, args.sheet)
    publishable = [r for r in records if is_publishable_row(r)]

    print(f"sheet={schema['sheet']} rows={len(records)} publishable={len(publishable)}")
    if args.dry_run:
        return 0

    os.environ.setdefault("PROMETHEUS_MULTIPROC_DIR", str(REPO_ROOT / "instance" / "prometheus_multiproc"))
    Path(os.environ["PROMETHEUS_MULTIPROC_DIR"]).mkdir(parents=True, exist_ok=True)

    from app import create_app
    from app.database.models import db
    from app.services.blog.sync import upsert_publishable_rows_from_raw_feed

    app = create_app(os.getenv("FLASK_ENV", "production"))
    with app.app_context():
        _ensure_blog_post_schema(db)
        stats = upsert_publishable_rows_from_raw_feed(records, db.session, logger=app.logger)
        print("import_stats:", stats)
        if stats.get("error"):
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
