import io


def test_media_upload_requires_token(client):
    for path in ("/api/media/upload", "/api/blog/media/upload"):
        rv = client.post(
            path,
            data={"file": (io.BytesIO(b"fake-image"), "cover.jpg")},
            content_type="multipart/form-data",
        )
        assert rv.status_code in (401, 503)


def test_media_upload_saves_file_and_returns_public_url(client, tmp_path):
    app = client.application
    app.config["MEDIA_UPLOAD_TOKEN"] = "test-token"
    app.config["SITE_BASE_URL"] = "https://mywavetraining.ru"
    app.config["MEDIA_UPLOAD_ROOT"] = str(tmp_path)
    app.config["MEDIA_UPLOAD_SUBDIR"] = "uploads/review_media"
    app.config["MEDIA_UPLOAD_MAX_BYTES"] = 1024 * 1024

    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "cover.png")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    payload = rv.get_json()
    assert payload["ok"] is True
    assert payload["public_url"].startswith("https://mywavetraining.ru/static/uploads/review_media/")
    u = payload["public_url"]
    assert payload.get("url") == u
    assert payload.get("cover_image_url") == u
    assert payload.get("image_url") == u

    saved = list((tmp_path / "uploads" / "review_media").glob("review_*"))
    assert len(saved) == 1
