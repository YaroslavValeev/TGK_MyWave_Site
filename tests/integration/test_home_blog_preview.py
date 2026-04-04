"""Главная: превью блога (4 последних поста)."""
from datetime import datetime


def _make_post(i: int):
    return {
        "title": f"Пост {i}",
        "slug": f"post-{i}",
        "excerpt": f"Кратко {i}",
        "cover_image_url": None,
        "published_at": datetime(2026, 3, i, 12, 0, 0),
    }


def test_home_includes_blog_cta_and_mocked_posts(client, mocker):
    fake_posts = [
        {
            "title": "Заголовок превью",
            "slug": "preview-slug-home",
            "excerpt": "Краткий текст",
            "cover_image_url": None,
            "published_at": datetime(2026, 3, 1, 12, 0, 0),
        }
    ]
    mocker.patch(
        "app.services.blog.store.get_posts",
        return_value=(fake_posts, 1),
    )
    rv = client.get("/")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert "Заголовок превью" in html
    assert "preview-slug-home" in html
    assert "Все публикации" in html
    assert "/blog" in html


def test_home_blog_empty_still_has_blog_link(client, mocker):
    mocker.patch(
        "app.services.blog.store.get_posts",
        return_value=([], 0),
    )
    rv = client.get("/")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert "Перейти в блог" in html


def test_home_renders_three_posts_and_direct_links(client, mocker):
    fake_posts = [_make_post(1), _make_post(2), _make_post(3)]
    mocker.patch("app.services.blog.store.get_posts", return_value=(fake_posts, 3))

    rv = client.get("/")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)

    assert html.count("class=\"service-card blog-home-card\"") == 3
    assert "href=\"/blog/post-1\"" in html
    assert "href=\"/blog/post-2\"" in html
    assert "href=\"/blog/post-3\"" in html


def test_home_renders_max_four_posts_when_more_available(client, mocker):
    fake_posts = [_make_post(1), _make_post(2), _make_post(3), _make_post(4)]
    mocker.patch("app.services.blog.store.get_posts", return_value=(fake_posts, 9))

    rv = client.get("/")
    assert rv.status_code == 200
    html = rv.get_data(as_text=True)
    assert html.count("class=\"service-card blog-home-card\"") == 4
    assert "Все публикации" in html


def test_home_order_matches_blog_order_for_same_source(client, mocker):
    # Эмулируем единый порядок: новые выше старых.
    home_posts = [_make_post(4), _make_post(3), _make_post(2), _make_post(1)]
    blog_posts = [_make_post(4), _make_post(3), _make_post(2), _make_post(1)]

    mocker.patch("app.services.blog.store.get_posts", return_value=(home_posts, 4))
    mocker.patch("app.routes.blog.get_posts", return_value=(blog_posts, 4))

    home_html = client.get("/").get_data(as_text=True)
    blog_html = client.get("/blog").get_data(as_text=True)

    assert home_html.find("Пост 4") < home_html.find("Пост 3") < home_html.find("Пост 2") < home_html.find("Пост 1")
    assert blog_html.find("Пост 4") < blog_html.find("Пост 3") < blog_html.find("Пост 2") < blog_html.find("Пост 1")
