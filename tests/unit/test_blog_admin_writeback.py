"""Unit tests for B4 admin write helpers."""
from app.config.blog_features import is_blog_admin_write_enabled
from app.services.blog.admin_writeback import ADMIN_WRITABLE_COLUMNS, _norm_tags, _safe_slug, _safe_https_url


def test_admin_writable_includes_body_and_video_not_raw_content():
    assert "final_posts" in ADMIN_WRITABLE_COLUMNS
    assert "video_url" in ADMIN_WRITABLE_COLUMNS
    assert "embed_url" in ADMIN_WRITABLE_COLUMNS
    assert "raw_content" not in ADMIN_WRITABLE_COLUMNS
    assert "excerpt" in ADMIN_WRITABLE_COLUMNS
    assert "seo_title" in ADMIN_WRITABLE_COLUMNS


def test_norm_tags_dedup():
    assert _norm_tags("News, Event, news") == "News, Event"


def test_safe_slug_ascii():
    assert _safe_slug("Hello World!!", "x").startswith("hello-world")


def test_safe_https_url():
    assert _safe_https_url("https://youtu.be/abc") == "https://youtu.be/abc"
    assert _safe_https_url("javascript:alert(1)") == ""
    assert _safe_https_url("/static/x.jpg") == "/static/x.jpg"


def test_blog_admin_write_default_off(monkeypatch):
    monkeypatch.delenv("BLOG_ADMIN_WRITE_ENABLED", raising=False)
    assert is_blog_admin_write_enabled() is False
    monkeypatch.setenv("BLOG_ADMIN_WRITE_ENABLED", "1")
    assert is_blog_admin_write_enabled() is True
