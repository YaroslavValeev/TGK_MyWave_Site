"""Smoke: маршрут /api/blog/diagnostics зарегистрирован."""


def test_blog_diagnostics_route(client):
    rv = client.get("/api/blog/diagnostics")
    assert rv.status_code == 200
    data = rv.get_json()
    assert "counts" in data
    assert "parser_source" in data
    assert "hint" in data
