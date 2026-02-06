import click
from flask.cli import with_appcontext
from app.database.models import db, Document
import os
import json


@click.group()
def kb():
    """Команды для работы с базой знаний"""
    pass


@kb.command("init")
@with_appcontext
def kb_init():
    """Создать схему базы знаний (knowledge_base.db)"""
    db.create_all()
    click.echo("Схема базы знаний создана.")


@kb.command("import")
@click.argument("path")
@with_appcontext
def kb_import(path):
    """Импортировать файл знаний в базу данных"""
    if not os.path.exists(path):
        click.echo(f"Файл {path} не найден.")
        return
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                doc = json.loads(line)
                # Ожидается, что doc содержит хотя бы content, опционально title/meta
                document = Document(
                    title=doc.get("title", "Без названия"),
                    content=doc["content"],
                    meta=doc.get("meta"),
                )
                db.session.add(document)
            except Exception as e:
                click.echo(f"Ошибка при импорте строки: {e}")
        db.session.commit()
    click.echo(f"Импорт из {path} завершён.")
