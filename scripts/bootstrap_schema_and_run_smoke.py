#!/usr/bin/env python3
"""Create DB schema (create_all) and run smoke tests via test_client.

This is a safer alternative to running Alembic migrations when migrations
cannot be applied automatically. It creates tables from SQLAlchemy models
and runs the same POST/GET/PATCH smoke sequence.
"""
import os
import sys
from pprint import pprint

root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, root)

os.environ["PROMETHEUS_MULTIPROC_DIR"] = os.path.join(root, "prometheus_multiproc")
os.environ["ENABLE_GOOGLE_SERVICES"] = "False"

from app import create_app
from app.database.models import db


def run():
    app = create_app("development")

    with app.app_context():
        print("Creating database schema via db.create_all()...")
        db.create_all()
        print("Schema created (or already present).")

        # Для тестов отключаем CSRF, чтобы programmatic client мог отправлять запросы
        app.config["WTF_CSRF_ENABLED"] = False

        with app.test_client() as client:
            # Create
            payload = {
                "name": "Test User",
                "email": "test@example.com",
                "phone": "+70000000000",
                "startDate": "2025-12-10",
                "days": 1,
                "level": "beginner",
                "message": "Тестовая бронь (create_all)",
            }
            print("\n--- POST /api/booking/create")
            resp = client.post("/api/booking/create", json=payload)
            print("status:", resp.status_code)
            try:
                data = resp.get_json()
            except Exception:
                data = resp.data.decode("utf-8")
            pprint(data)

            if not isinstance(data, dict) or data.get("status") != "success":
                print("\nCreate failed; aborting smoke test")
                return 2

            booking_id = data["booking"]["id"]

            # GET
            print(f"\n--- GET /api/booking/{booking_id}")
            resp = client.get(f"/api/booking/{booking_id}")
            print("status:", resp.status_code)
            try:
                pprint(resp.get_json())
            except Exception:
                print(resp.data.decode("utf-8"))

            # PATCH
            print(f"\n--- PATCH /api/booking/{booking_id} (status->confirmed)")
            resp = client.patch(
                f"/api/booking/{booking_id}", json={"status": "confirmed"}
            )
            print("status:", resp.status_code)
            try:
                pprint(resp.get_json())
            except Exception:
                print(resp.data.decode("utf-8"))

    return 0


if __name__ == "__main__":
    sys.exit(run())
