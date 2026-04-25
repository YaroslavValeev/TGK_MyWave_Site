from datetime import datetime


def _post(title: str, slug: str, excerpt: str = "", content_md: str = "", tags=None):
    return {
        "id": slug,
        "title": title,
        "slug": slug,
        "excerpt": excerpt,
        "content_md": content_md,
        "content_html": f"<p>{content_md}</p>" if content_md else "",
        "cover_image_url": None,
        "tags": tags or [],
        "published_at": datetime(2026, 3, 25, 12, 0, 0),
        "source_name": "Test",
    }


def test_blog_search_filters_by_query(client, mocker):
    posts = [
        _post("Новости лагеря", "camp-news", excerpt="Большой анонс"),
        _post("Тренировка за катером", "boat-training", excerpt="Техника"),
    ]
    mocker.patch("app.routes.blog.get_posts", return_value=(posts, len(posts)))

    rv = client.get("/blog?q=лагеря")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert "Новости лагеря" in html
    assert "Тренировка за катером" not in html


def test_blog_search_works_with_tag_filter(client, mocker):
    posts = [
        _post("A", "a", content_md="alpha content", tags=["news"]),
        _post("B", "b", content_md="alpha too", tags=["other"]),
    ]
    mocker.patch("app.routes.blog.get_posts", return_value=(posts, len(posts)))

    rv = client.get("/blog?tag=news&q=alpha")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert 'href="/blog/a"' in html
    assert 'href="/blog/b"' not in html
