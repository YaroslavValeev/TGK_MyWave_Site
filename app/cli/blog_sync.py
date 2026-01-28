"""
CLI команда для синхронизации блога из Google Sheets.
"""
import click
from flask.cli import with_appcontext

from app.database.models import db
from app.services.blog.sync import sync_blog_from_parser_tab


@click.command("blog-sync")
@with_appcontext
def blog_sync_command():
    """Синхронизирует блог из PARSER_TAB (Google Sheets) в локальную БД."""
    from flask import current_app
    stats = sync_blog_from_parser_tab(db.session, logger=current_app.logger)
    click.echo(f"blog-sync: {stats}")
