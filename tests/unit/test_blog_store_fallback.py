"""Проверки fallback: Sheets -> БД в blog.store."""

from datetime import datetime

from app.services.blog import store


def test_get_posts_falls_back_to_db_when_sheets_unavailable(mocker):
    db_posts = [
        {
            "id": "db-1",
            "title": "DB post",
            "slug": "db-post",
            "excerpt": "from db",
            "content_html": "<p>x</p>",
            "cover_image_url": None,
            "tags": [],
            "published_at": datetime(2026, 3, 25, 12, 0, 0),
            "status": "published",
        }
    ]

    mocker.patch("app.services.blog.store._load_from_sheets", return_value=[])
    mocker.patch("app.services.blog.store._load_from_db", return_value=db_posts)

    items, total = store.get_posts(page=1, limit=4, prefer_sheets=True)

    assert total == 1
    assert len(items) == 1
    assert items[0]["slug"] == "db-post"
