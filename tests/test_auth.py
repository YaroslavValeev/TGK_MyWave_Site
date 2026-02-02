import pytest
from app import create_app
from app.database.models import db, User


@pytest.fixture
def app():
    app = create_app()
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


def test_register_login_logout(client):
    # Регистрация нового пользователя
    rv = client.post(
        "/register",
        data={
            "username": "testuser",
            "email": "user@example.com",
            "password": "Password1",
        },
        follow_redirects=True,
    )
    assert "Регистрация успешна" in rv.get_data(as_text=True)

    # Логин с правильными данными
    rv = client.post(
        "/login",
        data={"email": "user@example.com", "password": "Password1"},
        follow_redirects=True,
    )
    assert "Вы вошли в систему" in rv.get_data(as_text=True)

    # Выход
    rv = client.get("/logout", follow_redirects=True)
    assert "Вы вышли" in rv.get_data(as_text=True)

    # Логин с некорректным паролем
    rv = client.post(
        "/login",
        data={"email": "user@example.com", "password": "wrong"},
        follow_redirects=True,
    )
    assert "Неверные учетные данные" in rv.get_data(as_text=True)
