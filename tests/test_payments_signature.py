import hmac
import hashlib
import json
import os

from app import create_app


def test_callback_signature(tmp_path, monkeypatch):
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    # Configure provider secret
    os.environ['CLOUDPAYMENTS_SECRET'] = 'test-secret'

    with app.app_context():
        from app.database.models import db
        db.create_all()
        client = app.test_client()

        # Create payment
        resp = client.post('/api/payments/create', json={'amount': 5000, 'provider': 'cloudpayments'})
        assert resp.status_code == 200
        data = resp.get_json()
        pid = data['payment_id']
        idemp = data['idempotency_key']

        # Prepare callback payload
        payload = json.dumps({'idempotency_key': idemp, 'status': 'paid', 'provider': 'cloudpayments'}).encode('utf-8')
        sig = hmac.new(b'test-secret', payload, hashlib.sha256).hexdigest()

        headers = {
            'Content-Type': 'application/json',
            'X-CloudPayments-Signature': sig
        }

        resp2 = client.post('/api/payments/callback', data=payload, headers=headers)
        assert resp2.status_code == 200
    assert resp2.get_json()['status'] == 'paid'