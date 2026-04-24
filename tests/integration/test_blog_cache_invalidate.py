"""Сброс кэша Sheets для витрины блога."""

import json


def test_blog_cache_invalidate_forbidden_without_token(client, app):
    app.config["MEDIA_UPLOAD_TOKEN"] = "secret-test-token"
    rv = client.post("/api/blog/cache/invalidate")
    assert rv.status_code == 403


def test_blog_cache_invalidate_ok_with_bearer(client, app):
    app.config["MEDIA_UPLOAD_TOKEN"] = "secret-test-token"
    rv = client.post(
        "/api/blog/cache/invalidate",
        headers={"Authorization": "Bearer secret-test-token"},
    )
    assert rv.status_code == 200
    data = json.loads(rv.data)
    assert data.get("ok") is True
