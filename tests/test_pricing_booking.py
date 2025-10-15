import json
from app import create_app


def test_pricing_calc_and_booking(tmp_path, monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        from app.database.models import db
        db.create_all()
        client = app.test_client()

        # Pricing calc
        resp = client.post('/api/pricing/calc', json={'base_zone_price': 10000, 'package': 'Pro', 'options': {'insurance': 500}})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['total_price'] > 0

        # Booking
        payload = {'name': 'Ivan', 'phone': '+70000000000', 'date': '2025-11-01', 'time': '10:00'}
        resp2 = client.post('/api/booking/create', json=payload)
        assert resp2.status_code == 200
        d2 = resp2.get_json()
        assert d2['status'] in ('confirmed', 'pending')