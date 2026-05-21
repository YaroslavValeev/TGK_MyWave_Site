"""Сброс кэша competitions_ticker."""

import json


def test_competitions_cache_invalidate_forbidden_without_token(client, app):
    app.config["MEDIA_UPLOAD_TOKEN"] = "secret-test-token"
    rv = client.post("/api/competitions/cache/invalidate")
    assert rv.status_code == 403


def test_competitions_cache_invalidate_ok_with_media_token(client, app):
    app.config["MEDIA_UPLOAD_TOKEN"] = "secret-test-token"
    rv = client.post(
        "/api/competitions/cache/invalidate",
        headers={"Authorization": "Bearer secret-test-token"},
    )
    assert rv.status_code == 200
    assert json.loads(rv.data).get("ok") is True


def test_competitions_cache_invalidate_ok_with_competitions_token(client, app):
    app.config["MEDIA_UPLOAD_TOKEN"] = "other-token"
    app.config["COMPETITIONS_CACHE_INVALIDATE_TOKEN"] = "competitions-only"
    rv = client.post(
        "/api/competitions/cache/invalidate",
        headers={"X-Media-Upload-Token": "competitions-only"},
    )
    assert rv.status_code == 200
