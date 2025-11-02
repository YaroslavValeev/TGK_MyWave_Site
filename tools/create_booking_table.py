"""Create booking table if it does not exist.

This script should be run from the project root with the virtualenv activated.
It imports the application, obtains the SQLAlchemy engine and creates the `booking`
table only if it is missing. This prepares the DB so Alembic migrations that alter
the `booking` table (for example add unique constraints) can run.

Usage:
  & "venv/Scripts/Activate.ps1"; python tools/create_booking_table.py
"""
import sys
from pathlib import Path
from sqlalchemy import inspect

# ensure project root on sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.database.models import db, Booking


def main():
    app = create_app('development')
    with app.app_context():
        # Flask-SQLAlchemy v3: use db.engine inside app context
        try:
            engine = db.engine
        except Exception:
            engine = db.get_engine(app)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        if 'booking' in tables:
            print('Table `booking` already exists — nothing to do.')
            return 0

        # Create only the booking table (use metadata.create_all with checkfirst)
        print('Creating `booking` table (if missing)...')
        db.metadata.create_all(bind=engine, tables=[Booking.__table__])
        print('Ensure step completed — booking table created or already existed.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
