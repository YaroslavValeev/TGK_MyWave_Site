from app.services.blog.store import (
    _embed_media_from_json,
    _extract_cover_image,
    _is_image_like_url,
    _normalize_row_from_sheets,
)
from app.services.blog.telegram_preview import (
    canonical_telegram_post_url,
    is_public_telegram_post_url,
    telegram_preview_img_src,
)
from app.services.blog.video_embed import first_video_url_in_text, looks_like_watchable_video


def _publishable_row(**kwargs):
    base = {
        "id": "row-media-1",
        "status": "PUBLISHED",
        "final_posts": "Текст поста для витрины.",
        "slug": "test-slug-media",
    }
    base.update(kwargs)
    return base


def test_telegram_cdn_without_extension_is_image():
    assert _is_image_like_url("https://cdn4.telegram-cdn.org/file/abc123")
    assert _is_image_like_url("https://cdn4.telesco.pe/file/xyz")
    assert not _is_image_like_url("https://t.me/wakedivision/520")
    assert not _is_image_like_url("/static/uploads/review_media/clip.mp4")


def test_cover_uses_lazy_telegram_preview_when_only_tme_link():
    row = {
        "image_url": "https://t.me/wakedivision/520",
        "source_url": "https://t.me/wakedivision/520",
        "media_json": '{"type":"telegram_post","post_url":"https://t.me/wakedivision/520"}',
    }
    cover = _extract_cover_image(row)
    assert cover.startswith("/blog/media/telegram-preview?u=")
    assert "t.me" in cover


def test_normalize_row_extracts_youtube_from_source_and_media_json_mp4():
    yt = _normalize_row_from_sheets(
        _publishable_row(source_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    )
    assert yt is not None
    assert yt["video_iframe_src"] == "https://www.youtube.com/embed/dQw4w9WgXcQ"

    mp4 = _normalize_row_from_sheets(
        _publishable_row(
            media_json='[{"type":"video","url":"https://cdn.example.com/clip.mp4"}]',
        )
    )
    assert mp4 is not None
    assert mp4["video_direct_file_url"] == "https://cdn.example.com/clip.mp4"
    assert "clip.mp4" not in (mp4["content_html"] or "")


def test_normalize_row_telegram_video_opens_as_link():
    out = _normalize_row_from_sheets(
        _publishable_row(
            source_url="https://t.me/wakedivision/777",
            media_json='{"type":"video","post_url":"https://t.me/wakedivision/777"}',
        )
    )
    assert out is not None
    assert out["video_open_url"] == "https://t.me/wakedivision/777"
    assert out["cover_image_url"].startswith("/blog/media/telegram-preview")


def test_embed_media_skips_telegram_page_as_video_tag():
    html = _embed_media_from_json(
        '[{"type":"video","url":"https://t.me/wakedivision/777"}]'
    )
    assert "<video" not in html


def test_embed_extra_image_appended_to_content():
    out = _normalize_row_from_sheets(
        _publishable_row(
            cover_image_url="https://cdn.example.com/full.jpg",
            media_json=(
                '[{"type":"image","url":"https://cdn.example.com/full.jpg"},'
                '{"type":"image","url":"https://cdn.example.com/extra.webp"}]'
            ),
        )
    )
    assert out is not None
    assert "extra.webp" in (out["content_html"] or "")
    assert out["cover_image_url"] == "https://cdn.example.com/full.jpg"


def test_telegram_post_url_allowlist():
    assert is_public_telegram_post_url("https://t.me/wakedivision/520")
    assert canonical_telegram_post_url("https://www.t.me/wakedivision/520/") == (
        "https://t.me/wakedivision/520"
    )
    assert not is_public_telegram_post_url("https://evil.example/t.me/x/1")
    assert not is_public_telegram_post_url("http://t.me/wakedivision/520")
    src = telegram_preview_img_src("https://t.me/wakedivision/520")
    assert src.startswith("/blog/media/telegram-preview?u=")


def test_first_video_url_in_text_finds_youtube():
    assert looks_like_watchable_video("https://youtu.be/dQw4w9WgXcQ")
    found = first_video_url_in_text("Смотри https://youtu.be/dQw4w9WgXcQ сегодня")
    assert found == "https://youtu.be/dQw4w9WgXcQ"


def test_parse_og_and_cdn_fallback_from_html():
    from app.services.blog.telegram_preview import _parse_cdn_image_fallback, _parse_og_image

    html = (
        '<meta property="og:image" content="https://cdn4.telesco.pe/file/abc123">'
        '<img src="https://cdn4.telesco.pe/file/extra.jpg">'
    )
    assert _parse_og_image(html).startswith("https://cdn4.telesco.pe/")
    embed = (
        '<a class="tgme_widget_message_photo_wrap" '
        'style="background-image:url(\'https://cdn4.telesco.pe/file/photo.jpg\')"></a>'
        '<video src="https://cdn4.telesco.pe/file/clip.mp4">'
    )
    assert _parse_cdn_image_fallback(embed).endswith("photo.jpg")
    assert ".mp4" not in _parse_cdn_image_fallback(embed)
