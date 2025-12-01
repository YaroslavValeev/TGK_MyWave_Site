#!/usr/bin/env python3
"""Smoke test for Safari booking API using Flask test client.

Runs POST /api/booking/create, GET /api/booking/<id>, PATCH /api/booking/<id>
and prints responses. This avoids running an external server.
"""
import sys
import os
import json
from pprint import pprint

# Ensure project root is on sys.path so `import app` works when run as script
root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, root)
import pathlib

# Ensure prometheus multiproc dir like main.py does
prom_dir = os.path.join(root, 'prometheus_multiproc')
os.makedirs(prom_dir, exist_ok=True)
os.environ['PROMETHEUS_MULTIPROC_DIR'] = prom_dir
os.environ['ENABLE_GOOGLE_SERVICES'] = 'False'

from app import create_app


def run():
    app = create_app('testing')
    with app.test_client() as client:
        # 1) Create
        payload = {
            'name': 'Test User',
            'email': 'test@example.com',
            'phone': '+70000000000',
            'startDate': '2025-12-10',
            'days': 1,
            'level': 'beginner',
            'message': 'Тестовая бронь от CI'
        }
        print('\n--- POST /api/booking/create')
        resp = client.post('/api/booking/create', json=payload)
        print('status:', resp.status_code)
        try:
            data = resp.get_json()
        except Exception:
            data = resp.data.decode('utf-8')
        pprint(data)

        if not isinstance(data, dict) or data.get('status') != 'success':
            print('\nCreate failed; aborting smoke test')
            return 2

        booking_id = data['booking']['id']

        # 2) GET
        print(f'\n--- GET /api/booking/{booking_id}')
        resp = client.get(f'/api/booking/{booking_id}')
        print('status:', resp.status_code)
        try:
            pprint(resp.get_json())
        except Exception:
            print(resp.data.decode('utf-8'))

        # 3) PATCH
        print(f'\n--- PATCH /api/booking/{booking_id} (status->confirmed)')
        resp = client.patch(f'/api/booking/{booking_id}', json={'status': 'confirmed'})
        print('status:', resp.status_code)
        try:
            pprint(resp.get_json())
        except Exception:
            print(resp.data.decode('utf-8'))

    return 0


if __name__ == '__main__':
    sys.exit(run())
