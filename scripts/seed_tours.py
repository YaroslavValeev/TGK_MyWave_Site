"""Seed demo tours into the development database.

Usage:
    PYTHONPATH=. python scripts/seed_tours.py

This script is intended for local development only. It will create tables
(if using sqlite) and insert several demo tours and packages if they don't exist.
"""
import os
from datetime import date, timedelta
import json

from pathlib import Path

# Add project root to path when executed directly

try:
    from app.database.models import db, Tour, TourPackage
    from app import create_app
except Exception as e:
    raise RuntimeError('This script must be run with project root on PYTHONPATH') from e

app = create_app()
with app.app_context():
    print('Creating database tables (if needed)...')
    try:
        db.create_all()
    except Exception as e:
        # SQLite sometimes raises OperationalError when indexes already exist.
        # Log and continue; tables may already exist from a previous run.
        import sqlalchemy
        if isinstance(e, sqlalchemy.exc.OperationalError) and 'already exists' in str(e):
            print('Database objects already exist, continuing...')
        else:
            raise

    # Check if any tours exist
    existing = Tour.query.count()
    if existing:
        print(f"{existing} tours already exist. Skipping seed.")
        raise SystemExit(0)

    print('Inserting demo tours...')

    today = date.today()
    tours = [
        {
            'region': 'Southern Coast',
            'city': 'Sochi',
            'start_date': today + timedelta(days=14),
            'end_date': today + timedelta(days=21),
            'level': 'M',
            'partner_club': 'Sochi Wake Club',
            'capacity': 12,
            'description': '7-day wakesurf camp on the Black Sea with daily coaching.',
            'packages': [
                {'name': 'Base', 'price_rub': 25000, 'includes': {'lessons': 5, 'meals': False}},
                {'name': 'Pro', 'price_rub': 42000, 'includes': {'lessons': 10, 'meals': True}},
                {'name': 'Elite', 'price_rub': 68000, 'includes': {'lessons': 15, 'meals': True, 'accommodation': True}},
            ]
        },
        {
            'region': 'Lakes',
            'city': 'Karelia',
            'start_date': today + timedelta(days=45),
            'end_date': today + timedelta(days=50),
            'level': 'N',
            'partner_club': 'Karelia Riders',
            'capacity': 10,
            'description': 'Weekend introduction to wakesurf on pristine lakes.',
            'packages': [
                {'name': 'Base', 'price_rub': 8000, 'includes': {'lessons': 3, 'meals': False}},
                {'name': 'Pro', 'price_rub': 14000, 'includes': {'lessons': 6, 'meals': True}},
            ]
        }
    ]

    for t in tours:
        tour = Tour(
            region=t['region'],
            city=t['city'],
            start_date=t['start_date'],
            end_date=t['end_date'],
            level=t['level'],
            partner_club=t['partner_club'],
            capacity=t['capacity'],
            description=t['description']
        )
        db.session.add(tour)
        db.session.flush()
        for p in t.get('packages', []):
            pkg = TourPackage(
                tour_id=tour.id,
                name=p['name'],
                price_rub=p['price_rub'],
                includes=p.get('includes', {}),
                available=True
            )
            db.session.add(pkg)

    db.session.commit()
    print('Seed completed.')
