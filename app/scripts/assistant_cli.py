import click
from flask import current_app
from app.database.models import db, Assistant
from app.services.openai_service import create_assistant
from config import Config

@click.group()
def cli():
    """CLI для управления ассистентом OpenAI."""
    pass

@cli.command()
def create():
    """Создаёт нового ассистента и сохраняет его в БД."""
    try:
        # Создаём ассистента через API
        assistant = create_assistant(
            name="Wakesurfing GPT",
            instructions="Ты эксперт по вейксерфингу. Отвечай подробно и понятно.",
            model=Config.GPTS_MODEL
        )
        
        # Сохраняем в БД
        db_assistant = Assistant(
            assistant_id=assistant.id,
            name=assistant.name,
            instructions=assistant.instructions,
            model=assistant.model
        )
        db.session.add(db_assistant)
        db.session.commit()
        
        click.echo(f"Ассистент создан! ID: {assistant.id}")
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        db.session.rollback()

@cli.command()
@click.argument('assistant_id')
@click.option('--name', help='Новое имя ассистента')
@click.option('--instructions', help='Новые инструкции')
@click.option('--model', help='Новая модель')
def update(assistant_id, name, instructions, model):
    """Обновляет существующего ассистента по ID."""
    from app.services.openai_service import client
    try:
        update_fields = {}
        if name:
            update_fields['name'] = name
        if instructions:
            update_fields['instructions'] = instructions
        if model:
            update_fields['model'] = model
        if not update_fields:
            click.echo("Нет новых данных для обновления.", err=True)
            return

        # Обновляем ассистента через OpenAI API
        updated = client.beta.assistants.update(
            assistant_id,
            **update_fields
        )

        # Обновляем в БД
        db_assistant = Assistant.query.filter_by(assistant_id=assistant_id).first()
        if db_assistant:
            if name:
                db_assistant.name = name
            if instructions:
                db_assistant.instructions = instructions
            if model:
                db_assistant.model = model
            db.session.commit()
            click.echo(f"Ассистент {assistant_id} обновлён.")
        else:
            click.echo("Ассистент не найден в базе данных.", err=True)
    except Exception as e:
        click.echo(f"Ошибка: {e}", err=True)
        db.session.rollback()

if __name__ == '__main__':
    cli() 