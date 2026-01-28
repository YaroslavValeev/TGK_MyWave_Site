"""
Миграция таблицы blog_post — добавление недостающих колонок.
Запуск: flask migrate-blog
"""
import click
from flask.cli import with_appcontext
from sqlalchemy import text


# Колонки, которые нужно добавить (если их нет)
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
]


@click.command("migrate-blog")
@with_appcontext
def migrate_blog_command():
    """Добавляет недостающие колонки в таблицу blog_post."""
    from app.database.models import db
    
    click.echo("🔄 Миграция таблицы blog_post...")
    
    conn = db.engine.connect()
    
    # Получаем существующие колонки
    try:
        result = conn.execute(text("PRAGMA table_info(blog_post)"))
        existing_columns = {row[1] for row in result.fetchall()}
        click.echo(f"   Существующие колонки: {existing_columns}")
    except Exception as e:
        click.echo(f"❌ Ошибка получения структуры таблицы: {e}")
        # Таблица не существует — создаём всё заново
        click.echo("   Создаю таблицы заново...")
        db.create_all()
        click.echo("✅ Таблицы созданы!")
        return
    
    added = 0
    for col_name, col_type in COLUMNS_TO_ADD:
        if col_name not in existing_columns:
            try:
                sql = f"ALTER TABLE blog_post ADD COLUMN {col_name} {col_type}"
                conn.execute(text(sql))
                conn.commit()
                click.echo(f"   ✅ Добавлена колонка: {col_name}")
                added += 1
            except Exception as e:
                click.echo(f"   ⚠️ Не удалось добавить {col_name}: {e}")
    
    conn.close()
    
    if added == 0:
        click.echo("ℹ️ Все колонки уже существуют, миграция не требуется.")
    else:
        click.echo(f"✅ Миграция завершена! Добавлено колонок: {added}")
