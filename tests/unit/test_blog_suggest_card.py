"""Тесты эвристик SEO/тегов и quality checklist для Admin Blog."""
from app.services.blog.suggest_card import (
    build_card_suggestions,
    evaluate_seo_card,
    merge_empty_with_suggestions,
    suggest_meta,
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
    assert "катер" in tags


def test_suggest_tags_online_coaching():
    tags = suggest_tags("Разбор техники", "Онлайн-коучинг и разбор видео ученика.")
    assert "онлайн-коучинг" in tags


def test_suggest_seo_title_length_and_brand():
    out = suggest_seo_title("Foiling Week 2026 Was a Big Success for All Competitors Everywhere")
    assert len(out) <= 60
    assert "MyWave" in out


def test_suggest_meta_adds_service_cta():
    meta = suggest_meta(
        "Свободные слоты",
        "",
        "Открыта запись на катер в выходные.",
    )
    assert "MyWave" in meta
    assert len(meta) <= 155


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
            "seo_title": "Уже задано вручную",
            "meta_description": "",
            "og_title": "",
            "og_description": "",
            "cover_image_url": "/static/images/Place1Logo.png",
            "slug": "train-boat",
        },
        suggestions,
    )
    assert merged["seo_title"] == "Уже задано вручную"
    assert merged["raw_tags"]
    assert "тренировки" in merged["raw_tags"] or "катер" in merged["raw_tags"]
    assert merged["meta_description"]
    assert merged["excerpt"]


def test_evaluate_seo_card_fails_without_cover_and_tags():
    score, checks = evaluate_seo_card(
        {
            "seo_title": "Нормальный заголовок новости | MyWave",
            "meta_description": "Достаточно длинное описание карточки для сниппета поиска и превью.",
            "raw_tags": "новости",
            "cover_image_url": "/static/images/Place1Logo.png",
            "slug": "ok-slug",
            "excerpt": "Лид",
            "og_title": "Нормальный заголовок новости | MyWave",
        }
    )
    levels = {c.code: c.level for c in checks}
    assert levels["tags_few"] == "fail"
    assert levels["cover_weak"] == "fail"
    assert score < 70
