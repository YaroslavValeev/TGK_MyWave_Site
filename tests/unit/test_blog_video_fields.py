"""Video-поля read-model блога (Sheets → store)."""

from app.services.blog.store import _normalize_row_from_sheets


def _publishable_row(**kwargs):
    base = {
        "id": "row-1",
        "status": "PUBLISHED",
        "final_posts": "Текст поста для витрины.",
        "slug": "test-slug-video",
    }
    base.update(kwargs)
    return base


def test_normalize_row_extracts_video_embed_and_poster():
    row = _publishable_row(
        embed_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        video_preview_image_url="https://cdn.example.com/poster.jpg",
    )
    out = _normalize_row_from_sheets(row)
    assert out is not None
    assert out["video_iframe_src"] == "https://www.youtube.com/embed/dQw4w9WgXcQ"
    assert out["card_image_url"] == "https://cdn.example.com/poster.jpg"
    assert out["video_poster_url"] == "https://cdn.example.com/poster.jpg"


def test_normalize_row_direct_mp4_sets_file_not_iframe():
    row = _publishable_row(
        video_url="https://cdn.example.com/clip.mp4",
        video_preview_image_url="https://cdn.example.com/thumb.jpg",
    )
    out = _normalize_row_from_sheets(row)
    assert out is not None
    assert out["video_direct_file_url"] == "https://cdn.example.com/clip.mp4"
    assert out["video_iframe_src"] is None
