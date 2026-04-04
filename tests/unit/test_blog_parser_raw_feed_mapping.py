from app.services.blog.publishability import is_publishable_row
from app.services.blog.store import (
    _card_excerpt_from_sources,
    _detect_parser_header_row,
    _extract_first_media,
    _extract_title_from_markdown,
    _make_excerpt_from_content,
    _normalize_row_from_sheets,
    _sanitize_preview_text,
    FALLBACK_BLOG_CARD_EXCERPT,
)
from app.services.blog.sync import _as_bool, _normalize_to_naive_utc


def test_extract_title_from_markdown_prefers_h1():
    md = "# Заголовок\n\nТекст"
    assert _extract_title_from_markdown(md) == "Заголовок"


def test_detect_parser_header_row_finds_real_header():
    rows = [
        ["1013", "rss", "https://example.com", "value"],
        ["legacy", "top", "block"],
        [
            "id",
            "source_type",
            "source_name",
            "source_url",
            "created_at",
            "ingest_status",
            "raw_title",
            "final_posts",
            "summary",
            "status",
            "slug",
            "published_at",
        ],
        ["1", "rss", "Заголовок", "# Пост", "Лид", "READY_TO_PUBLISH", "zagolovok", "2026-03-01"],
    ]
    idx = _detect_parser_header_row(rows)
    assert idx == 2


def test_detect_parser_header_row_rejects_hybrid_row():
    # Гибридная строка: в начале лежат данные поста (длинный контент),
    # а в хвосте — отдельные названия полей.
    hybrid = ["data"] * 80
    hybrid[0] = "This is long article content ... " + ("x" * 150)
    hybrid[1] = "Missing row_number (site_p0_test_20260128_105337)."
    hybrid[69] = "id"
    hybrid[70] = "source_type"
    hybrid[71] = "source_name"
    hybrid[72] = "source_url"
    hybrid[73] = "created_at"
    hybrid[74] = "ingest_status"
    hybrid[75] = "raw_title"
    hybrid[76] = "final_posts"
    hybrid[77] = "summary"
    hybrid[78] = "status"
    hybrid[79] = "slug"

    header = [
        "id",
        "source_type",
        "source_name",
        "source_url",
        "created_at",
        "ingest_status",
        "raw_title",
        "final_posts",
        "summary",
        "status",
        "slug",
        "published_at",
    ]

    rows = [
        hybrid,
        header,
    ]
    idx = _detect_parser_header_row(rows)
    assert idx == 1


def test_make_excerpt_from_html_content():
    html = "<p>Привет</p><p>мир parser news</p>"
    excerpt = _make_excerpt_from_content(html, limit=40)
    assert "Привет мир parser news" in excerpt


def test_extract_first_media_from_json_list():
    raw = '["https://example.com/img.jpg", "https://example.com/2.jpg"]'
    assert _extract_first_media(raw) == "https://example.com/img.jpg"


def test_publishable_bool_handling():
    assert _as_bool("TRUE")
    assert _as_bool("1")
    assert _as_bool("yes")
    assert not _as_bool("no")


def test_publishable_v1_contract():
    assert is_publishable_row(
        {"status": "READY_TO_PUBLISH", "final_posts": "# x", "published_posts": "TRUE"}
    )
    assert is_publishable_row({"status": "PUBLISHED", "text": "hello"})
    assert not is_publishable_row({"status": "", "published_posts": "TRUE", "final_posts": "# x"})
    assert not is_publishable_row({"status": "APPROVED", "final_posts": "# x"})
    assert not is_publishable_row({"status": "ARCHIVED", "final_posts": "# x"})
    assert not is_publishable_row({"status": "READY_TO_PUBLISH", "final_posts": ""})
    assert is_publishable_row({"status": "ready_to_publish", "final_posts": "ok"})


def test_normalize_to_naive_utc():
    from datetime import datetime, timezone

    naive = datetime(2026, 1, 1, 12, 0, 0)
    assert _normalize_to_naive_utc(naive) == naive
    aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    out = _normalize_to_naive_utc(aware)
    assert out.tzinfo is None
    assert out.hour == 12


def test_normalize_parser_row_with_fallbacks():
    row = {
        "id": "42",
        "raw_title": "",
        "final_posts": "# Новый пост\n\nКонтент поста",
        "summary": "",
        "lead": "",
        "raw_content": "Текст для выжимки",
        "cover_image_url": "",
        "image_url": "",
        "raw_media": "",
        "status": "READY_TO_PUBLISH",
        "published_posts": "TRUE",
        "slug": "",
        "raw_tags": "one,two",
    }
    post = _normalize_row_from_sheets(row)
    assert post is not None
    assert post["title"] == "Новый пост"
    assert post["excerpt"]
    assert "Контент поста" in post["excerpt"] or "Новый пост" in post["excerpt"]
    assert post["cover_image_url"] == "/static/images/Place1Logo.png"
    assert post["content_md"].startswith("# Новый пост")
    assert "updated_at" in post
    assert "author" in post


def test_sanitize_preview_strips_headings_and_test_tokens():
    raw = "# PO test\n\nThis is a record (site_p0_test_20260128_105337)."
    s = _sanitize_preview_text(raw)
    assert "#" not in s
    assert "site_p0_test" not in s.lower()
    assert "PO test" in s
    assert "This is a record" in s


def test_sanitize_drops_line_with_missing_row_number():
    raw = "# PO test Missing row_number (site_p0_test_missing_rn_20260128_105337)."
    assert _sanitize_preview_text(raw) == ""
    assert _card_excerpt_from_sources(raw) == FALLBACK_BLOG_CARD_EXCERPT


def test_normalize_row_po_multiline_excerpt_clean():
    row = {
        "id": "t2",
        "raw_title": "PO test",
        "final_posts": (
            "# PO test\n\n"
            "This is a PO integration test record (site_p0_test_20260128_105337)."
        ),
        "summary": "",
        "lead": "",
        "status": "READY_TO_PUBLISH",
        "slug": "po-test-2",
        "published_at": "2026-03-01",
    }
    post = _normalize_row_from_sheets(row)
    assert post is not None
    assert "site_p0" not in post["excerpt"].lower()
    assert "Missing row_number" not in post["excerpt"]
    assert "#" not in post["excerpt"]
    assert "integration test" in post["excerpt"].lower()
