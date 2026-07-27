import pytest


def test_extract_blog_sections_by_heading():
    from app.services.kb_chat.blog_ingest import extract_blog_sections

    md = """
# Заголовок

## Первый блок
Текст первого блока. Больше деталей.

## Второй блок
Текст второго блока. Ещё детали.

## Третий блок
Текст третьего блока.
""".strip()

    sections = extract_blog_sections(md, max_sections=2)
    assert len(sections) == 2
    assert sections[0][0] == "Первый блок"
    assert "Текст первого блока" in sections[0][1]
    assert sections[1][0] == "Второй блок"


def test_render_kb_card_md_contains_required_sections():
    from app.services.kb_chat.blog_ingest import _render_kb_card_md

    md = _render_kb_card_md(
        doc_id="blog_x_0",
        title="Секция",
        category="blog",
        priority="low",
        triggers=["Секция", "ключевое слово"],
        short_answer="Коротко",
        detailed_answer="Подробно",
        test_questions=["Вопрос 1", "Вопрос 2"],
        dont_say=["Не говорить X"],
        sources=["/blog/test"],
        blog_checksum="abc",
    )

    assert "id: blog_x_0" in md
    assert "## Когда использовать" in md
    assert "## Короткий ответ" in md
    assert "Коротко" in md
    assert "## Подробный ответ" in md
    assert "Подробно" in md
    assert "## Тестовые вопросы" in md

