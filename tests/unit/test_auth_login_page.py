"""Regression: /login must render (auth.login template exists)."""


def test_login_page_get_returns_200(client):
    resp = client.get("/login")
    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert "Вход в админ-панель" in body
    assert 'name="email"' in body
    assert 'name="password"' in body
