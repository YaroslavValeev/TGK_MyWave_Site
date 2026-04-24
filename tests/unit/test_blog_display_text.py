"""Тесты нормализации заголовков блога (витрина = sync/publish/store)."""
import pytest

from app.services.blog.display_text import plain_title_for_display


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("", ""),
        ("  ", ""),
        ("**Жирный** заголовок", "Жирный заголовок"),
        ("[текст](https://x) и ещё", "текст и ещё"),
        ("`код` в заголовке", "код в заголовке"),
        ("Материал abc-123", "Материал abc-123"),
    ],
)
def test_plain_title_for_display(raw: str, expected: str) -> None:
    assert plain_title_for_display(raw) == expected
