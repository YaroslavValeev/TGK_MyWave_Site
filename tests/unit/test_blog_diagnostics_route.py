"""Smoke: маршрут /api/blog/diagnostics — только с MEDIA_UPLOAD_TOKEN."""


def test_blog_diagnostics_forbidden_without_token(client, app):
    app.config["MEDIA_UPLOAD_TOKEN"] = "secret-diag-token"
    rv = client.get("/api/blog/diagnostics")
    assert rv.status_code == 403


def test_blog_diagnostics_ok_with_bearer(client, app):
    app.config["MEDIA_UPLOAD_TOKEN"] = "secret-diag-token"
    rv = client.get(
        "/api/blog/diagnostics",
        headers={"Authorization": "Bearer secret-diag-token"},
    )
    assert rv.status_code == 200
    data = rv.get_json()
    assert "counts" in data
    assert "parser_source" in data
    assert "hint" in data
