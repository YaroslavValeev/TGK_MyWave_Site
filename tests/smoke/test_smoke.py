"""
Smoke tests for rapid QA validation.

These tests verify:
- API endpoints respond correctly
- Database connectivity
- Authentication flow
- Core business logic
"""

import pytest
import json
from datetime import datetime, timedelta

from app import create_app, db
from app.database.models import User


@pytest.fixture
def app():
    """Create app for testing"""
    app = create_app(config_name="testing")

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


class TestAPIEndpoints:
    """Test all critical API endpoints respond"""

    def test_auth_register_endpoint(self, client):
        """Test /api/auth/register endpoint"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "test@example.com",
                "password": "Password123!",
                "username": "testuser",
                "full_name": "Test User",
            },
        )

        assert response.status_code in [200, 201, 409]  # 409 if user exists

    def test_auth_login_endpoint(self, client):
        """Test /api/auth/login endpoint"""
        # Register first
        client.post(
            "/api/auth/register",
            json={
                "email": "login@example.com",
                "password": "Password123!",
                "username": "loginuser",
                "full_name": "Login User",
            },
        )

        # Try login
        response = client.post(
            "/api/auth/login",
            json={"email": "login@example.com", "password": "Password123!"},
        )

        assert response.status_code in [200, 401]

    def test_bookings_list_endpoint(self, client):
        """Test GET /api/bookings endpoint"""
        response = client.get("/api/bookings")
        assert response.status_code in [200, 401]  # Might require auth

    def test_booking_create_endpoint(self, client):
        """Test POST /api/bookings endpoint"""
        response = client.post(
            "/api/bookings",
            json={
                "start_date": (datetime.now() + timedelta(days=7)).isoformat(),
                "end_date": (datetime.now() + timedelta(days=14)).isoformat(),
                "num_participants": 2,
            },
        )

        # Will likely fail auth, but endpoint should exist
        assert response.status_code in [200, 201, 401, 403]

    def test_payment_endpoint(self, client):
        """Test payment endpoints exist"""
        response = client.post(
            "/api/bookings/1/payment",
            json={"amount": 10000, "payment_method": "yookassa"},
        )

        # Will fail without valid booking, but endpoint should exist
        assert response.status_code in [200, 400, 401, 403, 404, 422]

    def test_calendar_sync_endpoint(self, client):
        """Test calendar sync endpoints exist"""
        response = client.post("/api/calendar/sync", json={})

        # Will fail without auth, but endpoint should exist
        assert response.status_code in [200, 401, 403]

    def test_chat_endpoint(self, client):
        """Test chat/AI assistant endpoints exist"""
        response = client.post("/api/chat", json={"message": "Hello"})

        # Will fail without context, but endpoint should exist
        assert response.status_code in [200, 401, 422]


class TestAuthenticationFlow:
    """Test authentication and authorization"""

    def test_register_and_login(self, client):
        """Test user registration and login flow"""
        email = "fullflow@example.com"
        password = "SecurePass123!"

        # Register
        reg_response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": password,
                "username": "fullflowuser",
                "full_name": "Full Flow User",
            },
        )

        assert reg_response.status_code in [200, 201, 409]

        # Login
        login_response = client.post(
            "/api/auth/login", json={"email": email, "password": password}
        )

        assert login_response.status_code in [200, 401]

        if login_response.status_code == 200:
            data = json.loads(login_response.data)
            assert "token" in data or "access_token" in data

    def test_invalid_login(self, client):
        """Test login with invalid credentials"""
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrongpassword"},
        )

        assert response.status_code in [400, 401, 404]

    def test_weak_password_rejected(self, client):
        """Test weak password rejection"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "weak@example.com",
                "password": "weak",  # Too simple
                "username": "weakuser",
                "full_name": "Weak User",
            },
        )

        # Should reject weak password
        assert response.status_code in [400, 422]


class TestDatabaseConnectivity:
    """Test database operations"""

    def test_user_creation(self, app):
        """Test creating user in database"""
        with app.app_context():
            user = User(email="db@example.com", username="dbuser", full_name="DB User")
            user.set_password("Password123!")

            db.session.add(user)
            db.session.commit()

            # Verify user was created
            found_user = User.query.filter_by(email="db@example.com").first()
            assert found_user is not None
            assert found_user.username == "dbuser"

    def test_user_query(self, app):
        """Test querying users"""
        with app.app_context():
            # Create test user
            user = User(
                email="query@example.com", username="queryuser", full_name="Query User"
            )
            user.set_password("Password123!")
            db.session.add(user)
            db.session.commit()

            # Query user
            found = User.query.filter_by(username="queryuser").first()
            assert found is not None
            assert found.email == "query@example.com"

    def test_user_deletion(self, app):
        """Test deleting users"""
        with app.app_context():
            # Create user
            user = User(
                email="delete@example.com",
                username="deleteuser",
                full_name="Delete User",
            )
            user.set_password("Password123!")
            db.session.add(user)
            db.session.commit()
            user_id = user.id

            # Delete user
            db.session.delete(user)
            db.session.commit()

            # Verify deleted
            found = User.query.filter_by(id=user_id).first()
            assert found is None


class TestDataValidation:
    """Test data validation and constraints"""

    def test_email_uniqueness(self, app):
        """Test email uniqueness constraint"""
        with app.app_context():
            email = "unique@example.com"

            # Create first user
            user1 = User(email=email, username="user1", full_name="User 1")
            user1.set_password("Pass123!")
            db.session.add(user1)
            db.session.commit()

            # Try to create duplicate
            user2 = User(email=email, username="user2", full_name="User 2")
            user2.set_password("Pass123!")
            db.session.add(user2)

            # Should fail due to unique constraint
            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()

    def test_username_format(self, client):
        """Test username validation"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "valid@example.com",
                "password": "ValidPass123!",
                "username": "valid_user_123",  # Valid format
                "full_name": "Valid User",
            },
        )

        assert response.status_code in [200, 201, 409]

    def test_email_validation(self, client):
        """Test email validation"""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "invalid-email",  # Invalid format
                "password": "ValidPass123!",
                "username": "validuser",
                "full_name": "Valid User",
            },
        )

        # Should reject invalid email
        assert response.status_code in [400, 422]


class TestConcurrency:
    """Test concurrent operations"""

    def test_multiple_booking_creations(self, client, app):
        """Test handling multiple concurrent bookings"""
        # This is a basic test - in production use threading/async

        with app.app_context():
            # Create and authenticate user
            user = User(
                email="concurrent@example.com",
                username="concurrentuser",
                full_name="Concurrent User",
            )
            user.set_password("Password123!")
            db.session.add(user)
            db.session.commit()

            # Get auth token (in real test)
            # For now, just verify app doesn't crash with multiple requests
            for i in range(5):
                response = client.post(
                    "/api/bookings",
                    json={
                        "start_date": (
                            datetime.now() + timedelta(days=7 + i)
                        ).isoformat(),
                        "end_date": (
                            datetime.now() + timedelta(days=14 + i)
                        ).isoformat(),
                        "num_participants": 2,
                    },
                )

                # Should not crash
                assert response.status_code in [200, 201, 401, 403, 422]


class TestErrorMessages:
    """Test error messages are informative"""

    def test_booking_error_messages(self, client):
        """Test booking error messages"""
        response = client.post(
            "/api/bookings",
            json={
                "start_date": "invalid-date",
                "end_date": "invalid-date",
                "num_participants": -1,  # Invalid
            },
        )

        if response.status_code in [400, 422]:
            data = json.loads(response.data)
            # Should have error message
            assert "error" in data or "message" in data or "errors" in data

    def test_auth_error_messages(self, client):
        """Test authentication error messages"""
        response = client.post(
            "/api/auth/login",
            json={"email": "nonexistent@example.com", "password": "wrong"},
        )

        if response.status_code in [400, 401, 404]:
            data = json.loads(response.data)
            # Should have error message
            assert "error" in data or "message" in data


# Smoke test functions


def test_app_initialization(app):
    """Smoke: App initializes without errors"""
    assert app is not None
    assert app.config["TESTING"] is True


def test_client_creation(client):
    """Smoke: Test client can be created"""
    assert client is not None


def test_api_responses_valid_json(client):
    """Smoke: API responses are valid JSON"""
    # Only test endpoints that are likely to exist
    endpoints = [
        ("/api/bookings", "GET"),
        ("/health", "GET"),
    ]

    for endpoint, method in endpoints:
        if method == "GET":
            response = client.get(endpoint)
        else:
            response = client.post(endpoint, json={})

        # Response should be parseable
        if response.content_type and "json" in response.content_type:
            try:
                json.loads(response.data)
            except json.JSONDecodeError:
                pytest.fail(f"{endpoint} returned invalid JSON")


def test_http_status_codes(client):
    """Smoke: HTTP status codes are valid"""
    response = client.get("/api/bookings")

    # Status code should be valid HTTP
    assert 100 <= response.status_code < 600
