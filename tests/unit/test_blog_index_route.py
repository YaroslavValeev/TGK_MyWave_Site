"""Blog index must return 200 even when there are no posts."""


def test_blog_index_returns_200(client):
    resp = client.get("/blog")
    assert resp.status_code == 200
    assert b"blog-index" in resp.data or b"blog-card" in resp.data or b"/blog/" in resp.data
