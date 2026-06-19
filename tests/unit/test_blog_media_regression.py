import io

from app.services.blog.publish import _resolve_publish_cover
from app.services.blog.store import (
    _embed_media_from_json,
    _extract_cover_image,
    _normalize_media_url,
)


def test_normalize_media_url_rewrites_localhost_to_relative():
    assert (
        _normalize_media_url(
            "http://127.0.0.1:5000/static/uploads/review_media/review_abc.jpg"
        )
        == "/static/uploads/review_media/review_abc.jpg"
    )
    assert (
        _normalize_media_url(
            "http://localhost/static/uploads/review_media/review_abc.jpg"
        )
        == "/static/uploads/review_media/review_abc.jpg"
    )
    assert _normalize_media_url("https://cdn.example.com/a.jpg") == "https://cdn.example.com/a.jpg"


def test_embed_media_from_json_renders_image_html():
    raw = (
        '[{"type":"image","url":"https://cdn.example.com/full.jpg"},'
        '{"type":"image","url":"https://cdn.example.com/extra.webp"}]'
    )
    html = _embed_media_from_json(raw, exclude_url="https://cdn.example.com/full.jpg")
    assert "blog-post-embedded-media" in html
    assert "https://cdn.example.com/extra.webp" in html
    assert "https://cdn.example.com/full.jpg" not in html


def test_publish_cover_uses_extract_cover_image():
    row = {
        "cover_image_url": "http://127.0.0.1:5000/static/uploads/review_media/review_x.jpg",
        "image_url": "",
        "raw_media": "",
    }
    assert _resolve_publish_cover(row) == _extract_cover_image(row)
    assert _resolve_publish_cover(row) == "/static/uploads/review_media/review_x.jpg"


def test_media_upload_without_site_base_returns_relative_not_localhost(client, tmp_path):
    app = client.application
    app.config["MEDIA_UPLOAD_TOKEN"] = "test-token"
    app.config.pop("SITE_BASE_URL", None)
    app.config.pop("PUBLIC_BASE_URL", None)
    app.config.pop("BASE_URL", None)
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
    public_url = payload["public_url"]
    assert public_url.startswith("/static/uploads/review_media/")
    assert "127.0.0.1" not in public_url
    assert "localhost" not in public_url
