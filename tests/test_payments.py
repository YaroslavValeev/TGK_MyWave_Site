import json

from app import create_app


def test_create_and_callback(tmp_path, monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    # Disable CSRF for tests
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        from app.database.models import db
        # db is already initialized by create_app(); just create tables for testing
        db.create_all()

        client = app.test_client()
        # Create payment
        resp = client.post('/api/payments/create', json={'amount': 1000})
        assert resp.status_code == 200
        data = resp.get_json()
        assert 'payment_id' in data
        pid = data['payment_id']

        # Callback: mark as paid
        resp2 = client.post('/api/payments/callback', json={'idempotency_key': data['idempotency_key'], 'status': 'paid'})
        assert resp2.status_code == 200
        data2 = resp2.get_json()
        assert data2['status'] == 'paid'