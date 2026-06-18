import io

import pytest


def _media_upload_config(app, tmp_path, **overrides):
    app.config["MEDIA_UPLOAD_TOKEN"] = "test-token"
    app.config["MEDIA_UPLOAD_ROOT"] = str(tmp_path)
    app.config["MEDIA_UPLOAD_SUBDIR"] = "uploads/review_media"
    app.config["MEDIA_UPLOAD_MAX_BYTES"] = 1024 * 1024
    app.config["SITE_BASE_URL"] = "https://mywavewake.ru"
    for key, value in overrides.items():
        app.config[key] = value


def _minimal_jpeg() -> bytes:
    # Minimal valid JPEG header + padding (Parser-style real image smoke).
    return b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00\xff\xd9"


def test_media_upload_requires_token(client):
    for path in ("/api/media/upload", "/api/blog/media/upload"):
        rv = client.post(
            path,
            data={"file": (io.BytesIO(b"fake-image"), "cover.jpg")},
            content_type="multipart/form-data",
        )
        assert rv.status_code in (401, 503)
        if rv.status_code == 401:
            assert rv.is_json
            assert rv.get_json().get("error") == "unauthorized"


def test_media_upload_invalid_token_returns_401_json(client, tmp_path):
    _media_upload_config(client.application, tmp_path)
    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer wrong-token"},
        data={"file": (io.BytesIO(_minimal_jpeg()), "cover.jpg")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 401
    assert rv.is_json
    assert rv.get_json() == {"error": "unauthorized"}


def test_media_upload_no_file_returns_400_json(client, tmp_path):
    _media_upload_config(client.application, tmp_path)
    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 400
    assert rv.is_json
    assert rv.get_json() == {"error": "file is required"}


def test_media_upload_saves_file_and_returns_public_url(client, tmp_path):
    _media_upload_config(client.application, tmp_path)

    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (io.BytesIO(b"\x89PNG\r\n\x1a\nfake"), "cover.png")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    payload = rv.get_json()
    assert payload["ok"] is True
    assert payload["public_url"].startswith("https://mywavewake.ru/static/uploads/review_media/")
    u = payload["public_url"]
    assert payload.get("url") == u
    assert payload.get("cover_image_url") == u
    assert payload.get("image_url") == u
    assert "127.0.0.1" not in u
    assert "localhost" not in u

    saved = list((tmp_path / "uploads" / "review_media").glob("review_*"))
    assert len(saved) == 1
    assert saved[0].stat().st_size > 0
    legacy_saved = list((tmp_path / "downloads").glob("review_*"))
    assert len(legacy_saved) == 1
    assert legacy_saved[0].read_bytes() == saved[0].read_bytes()


def test_media_upload_real_jpg_item112_style_filename(client, tmp_path):
    _media_upload_config(client.application, tmp_path)
    body = _minimal_jpeg() * 50  # small but non-trivial payload

    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={
            "file": (
                io.BytesIO(body),
                "item-112-owner-cover.jpg",
                "image/jpeg",
            )
        },
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    payload = rv.get_json()
    assert payload["ok"] is True
    assert payload["public_url"].endswith(".jpg")
    assert payload["bytes"] == len(body)

    saved = list((tmp_path / "uploads" / "review_media").glob("review_*.jpg"))
    assert len(saved) == 1
    assert saved[0].read_bytes() == body


def test_media_upload_auto_creates_upload_directory(client, tmp_path):
    _media_upload_config(client.application, tmp_path)
    upload_dir = tmp_path / "uploads" / "review_media"
    assert not upload_dir.exists()

    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (io.BytesIO(_minimal_jpeg()), "cover.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    assert upload_dir.is_dir()
    assert list(upload_dir.glob("review_*"))


def test_media_upload_oversized_file_returns_413_json(client, tmp_path):
    _media_upload_config(client.application, tmp_path, MEDIA_UPLOAD_MAX_BYTES=16)
    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (io.BytesIO(_minimal_jpeg()), "big.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 413
    assert rv.is_json
    assert "file too large" in rv.get_json().get("error", "")


def test_media_upload_unsupported_mime_returns_415_json(client, tmp_path):
    _media_upload_config(client.application, tmp_path)
    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (io.BytesIO(b"not-an-image"), "doc.pdf", "application/pdf")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 415
    assert rv.get_json() == {"error": "unsupported file type"}


def test_media_upload_mkdir_failure_returns_507_json(client, tmp_path, monkeypatch):
    _media_upload_config(client.application, tmp_path)

    def _fail_mkdir(*_args, **_kwargs):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr("app.routes.api.os.makedirs", _fail_mkdir)

    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (io.BytesIO(_minimal_jpeg()), "cover.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 507
    assert rv.is_json
    assert rv.get_json() == {"error": "upload storage unavailable"}


def test_media_upload_save_failure_returns_507_json(client, tmp_path, monkeypatch):
    _media_upload_config(client.application, tmp_path)

    def _fail_save(_self, _path):
        raise OSError(13, "Permission denied")

    monkeypatch.setattr("werkzeug.datastructures.FileStorage.save", _fail_save)

    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (io.BytesIO(_minimal_jpeg()), "cover.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 507
    assert rv.is_json
    assert rv.get_json() == {"error": "upload write failed"}


def test_media_upload_file_size_non_seekable_stream(client, tmp_path):
    _media_upload_config(client.application, tmp_path)
    payload = _minimal_jpeg()

    class _NonSeekable(io.BytesIO):
        def seekable(self):
            return False

        def seek(self, *_args, **_kwargs):
            raise io.UnsupportedOperation("seek")

    rv = client.post(
        "/api/blog/media/upload",
        headers={"Authorization": "Bearer test-token"},
        data={"file": (_NonSeekable(payload), "cover.jpg", "image/jpeg")},
        content_type="multipart/form-data",
    )
    assert rv.status_code == 201
    assert rv.get_json()["bytes"] == len(payload)


@pytest.mark.parametrize(
    ("headers", "form_fields"),
    [
        ({"Authorization": "Token test-token"}, {}),
        ({"X-Upload-Token": "test-token"}, {}),
        ({"X-API-Key": "test-token"}, {}),
        ({}, {"upload_token": "test-token"}),
    ],
)
def test_media_upload_accepts_legacy_parser_auth_formats(client, tmp_path, headers, form_fields):
    _media_upload_config(client.application, tmp_path)
    payload = dict(form_fields)
    payload["file"] = (io.BytesIO(b"\x89PNG\r\n\x1a\nlegacy"), "cover.png")

    rv = client.post(
        "/api/media/upload",
        headers=headers,
        data=payload,
        content_type="multipart/form-data",
    )

    assert rv.status_code == 201
    body = rv.get_json()
    assert body["ok"] is True
    assert body["public_url"].endswith(body["filename"])
