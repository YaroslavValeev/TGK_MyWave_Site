"""CLI: periodic camp import from MyWaveTour."""

import click
from flask.cli import with_appcontext

from app.services.camps.import_service import sync_camps_from_tour


@click.command("camp-sync")
@with_appcontext
@click.option("--updated-since", default=None, help="ISO datetime for incremental sync")
def camp_sync_command(updated_since):
    """Import camps from MyWaveTour feed into local DB."""
    from datetime import datetime

    from flask import current_app

    since = datetime.fromisoformat(updated_since) if updated_since else None
    stats = sync_camps_from_tour(updated_since=since)
    current_app.logger.info("camp_sync_done", extra=stats)
    click.echo(f"camp-sync: {stats}")
