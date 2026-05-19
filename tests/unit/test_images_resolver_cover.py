"""Порядок обложки услуг (cover_index)."""
import pytest

from app.services.images_resolver import rotate_images_to_cover_index, scan_folder_images


def test_rotate_noop() -> None:
    assert rotate_images_to_cover_index([], 1) == []
    assert rotate_images_to_cover_index(["a"], 1) == ["a"]
    assert rotate_images_to_cover_index(["a", "b"], 0) == ["a", "b"]
    assert rotate_images_to_cover_index(["a", "b"], 2) == ["a", "b"]


def test_rotate_second_first() -> None:
    assert rotate_images_to_cover_index(["a", "b", "c"], 1) == ["b", "c", "a"]


def test_rotate_third_first() -> None:
    assert rotate_images_to_cover_index(["a", "b", "c", "d"], 2) == ["c", "d", "a", "b"]


def test_scan_skips_dotfiles() -> None:
    imgs = scan_folder_images("images/Services/Gym")
    assert imgs
    assert not any(part.startswith(".") for p in imgs for part in p.split("/"))
    assert not any(".trashed" in p for p in imgs)
