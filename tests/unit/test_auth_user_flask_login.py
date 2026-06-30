"""Regression: User model must satisfy Flask-Login contract."""

import pytest

from app.database.models import User, db


@pytest.fixture
def app():
    from app import create_app

    app = create_app("testing")
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
        }
    )
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_user_has_flask_login_interface():
    user = User(
        username="admin",
        email="admin@example.com",
        is_admin=True,
        role="admin",
    )
    user.set_password("Password1234")
    user.id = 1

    assert user.is_active is True
    assert user.is_authenticated is True
    assert user.is_anonymous is False
    assert user.get_id() == "1"


def test_login_user_does_not_raise_attribute_error(app):
    """Reproduces production path: login_user(user) after successful password check."""
    with app.app_context():
        user = User(
            username="qa_admin",
            email="qa_admin@example.com",
            is_admin=True,
            role="admin",
        )
        user.set_password("Password1234")
        db.session.add(user)
        db.session.commit()

        from flask_login import login_user

        with app.test_request_context():
            login_user(user)
