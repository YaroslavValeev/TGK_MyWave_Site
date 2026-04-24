"""Согласованность полей обложки между /api/blog/latest и /api/blog/posts."""
from datetime import datetime


def test_api_blog_latest_exposes_same_cover_keys_as_posts_items(client, mocker):
    post = {
        "title": "Заголовок",
        "slug": "zagolovok",
        "excerpt": "Лид",
        "published_at": datetime(2026, 4, 23, 12, 0, 0),
        "tags": ["news"],
        "cover_image_url": "https://example.com/cover.jpg",
        "image_url": "https://example.com/cover.jpg",
        "cover": "https://example.com/cover.jpg",
    }
    mocker.patch("app.routes.blog.get_latest_post", return_value=post)
    mocker.patch("app.routes.blog.get_posts", return_value=([post], 1))

    latest = client.get("/api/blog/latest").get_json()
    items = client.get("/api/blog/posts?limit=1").get_json()["items"][0]

    for key in ("cover_image_url", "image_url", "cover"):
        assert key in latest
        assert key in items
        assert latest[key] == items[key] == post[key]
