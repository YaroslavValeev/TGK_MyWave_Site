"""PR53.2 blog mobile layout evidence."""

def test_blog_index_has_vertical_grid_class(client):
    html = client.get("/blog").get_data(as_text=True)
    assert "blog-index-grid" in html
    assert "blog-card--listing" in html
