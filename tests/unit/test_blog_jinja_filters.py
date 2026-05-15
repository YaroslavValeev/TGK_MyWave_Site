from app.services.blog.display_text import plain_excerpt_for_display, plain_title_for_display


def test_plain_title_strips_markdown():
    assert plain_title_for_display("**Заголовок**") == "Заголовок"


def test_plain_excerpt_truncates():
    raw = "# Intro\n\n" + ("word " * 80)
    out = plain_excerpt_for_display(raw, limit=50)
    assert len(out) <= 55
    assert out.endswith("…")
