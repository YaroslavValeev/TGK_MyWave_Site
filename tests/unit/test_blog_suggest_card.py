"""Тесты эвристик SEO/тегов для Admin Blog."""
from app.services.blog.suggest_card import (
    build_card_suggestions,
    merge_empty_with_suggestions,
    suggest_seo_title,
    suggest_tags,
)


def test_suggest_tags_from_contest_text():
    tags = suggest_tags(
        "WILL IT SURF CONTEST фестиваль",
        "Регистрация на соревнования по вейксёрфингу у катера.",
    )
    assert "соревнования" in tags
    assert "вейксёрфинг" in tags


def test_suggest_seo_title_adds_brand():
    out = suggest_seo_title("Foiling Week 2026")
    assert "MyWave" in out
    assert out.startswith("Foiling Week")


def test_merge_fills_only_empty():
    post = {
        "title": "Тренировки на катере MyWave",
        "excerpt": "",
        "content_md": "Запись на тренировки и онлайн-коучинг.",
        "cover_image_url": "/static/images/Place1Logo.png",
        "slug": "train-boat",
    }
    suggestions = build_card_suggestions(post)
    merged = merge_empty_with_suggestions(
        {
            "excerpt": "",
            "raw_tags": "",
            "seo_title": "Уже задано",
            "meta_description": "",
            "og_title": "",
            "og_description": "",
            "cover_image_url": "/static/images/Place1Logo.png",
            "slug": "train-boat",
        },
        suggestions,
    )
    assert merged["seo_title"] == "Уже задано"
    assert merged["raw_tags"]
    assert "тренировки" in merged["raw_tags"] or "катер" in merged["raw_tags"]
    assert merged["meta_description"]
    assert merged["excerpt"]
