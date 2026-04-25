"""Порядок обложки услуг (cover_index)."""
import pytest

from app.services.images_resolver import rotate_images_to_cover_index


def test_rotate_noop() -> None:
    assert rotate_images_to_cover_index([], 1) == []
    assert rotate_images_to_cover_index(["a"], 1) == ["a"]
    assert rotate_images_to_cover_index(["a", "b"], 0) == ["a", "b"]
    assert rotate_images_to_cover_index(["a", "b"], 2) == ["a", "b"]


def test_rotate_second_first() -> None:
    assert rotate_images_to_cover_index(["a", "b", "c"], 1) == ["b", "c", "a"]


def test_rotate_third_first() -> None:
    assert rotate_images_to_cover_index(["a", "b", "c", "d"], 2) == ["c", "d", "a", "b"]
