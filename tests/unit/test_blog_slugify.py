"""ASCII slug для новых постов без sheet slug."""
from app.services.blog.sync import _slugify


def test_slugify_transliterates_cyrillic() -> None:
    slug = _slugify("Открыта регистрация на ROWSC", "id-42")
    assert slug.startswith("otkryta-registratsiya-na-rowsc-")
    assert slug.isascii()
    assert " " not in slug


def test_slugify_strips_emoji_and_limits_length() -> None:
    long_title = "🏄 " + ("длинный заголовок " * 20)
    slug = _slugify(long_title, "post-1")
    stem, _, suffix = slug.rpartition("-")
    assert suffix  # md5 short
    assert stem.isascii()
    assert len(stem) <= 50
