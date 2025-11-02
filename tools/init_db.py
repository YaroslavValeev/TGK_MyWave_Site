"""Initialize database by creating all tables from models.

This will call SQLAlchemy's create_all to ensure every model table exists.
Use with caution on production systems — it's intended for local/dev environments
when the DB was created without running the full migration history.

Usage:
  & "venv/Scripts/Activate.ps1"; python tools/init_db.py
"""
import sys
from pathlib import Path

# ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.database.models import db


def main():
    app = create_app('development')
    with app.app_context():
        print('Creating all tables (if missing)...')
        db.create_all()
        print('db.create_all() finished.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
