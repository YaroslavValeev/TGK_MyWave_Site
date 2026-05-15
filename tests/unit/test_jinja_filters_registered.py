"""Jinja filters must be registered after create_app completes."""


def test_mw_plain_filters_registered(app):
    assert "mw_plain_title" in app.jinja_env.filters
    assert "mw_plain_excerpt" in app.jinja_env.filters
    assert app.jinja_env.filters["mw_plain_title"]("**x**") == "x"
