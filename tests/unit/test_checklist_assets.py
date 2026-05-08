"""Маппинг фонов карточек чеклиста указывает на существующие файлы."""
import re
from pathlib import Path


def test_checklist_background_images_exist():
    root = Path(__file__).resolve().parents[2]
    js = (root / "static/js/checklist.js").read_text(encoding="utf-8")
    img_root = root / "static/images/Project/Cards/checklist"
    paths = set(re.findall(r"'[^']+': '([^']+\.webp)'", js))
    assert paths, "CHECKLIST_CARD_BACKGROUNDS appears empty or regex outdated"
    missing = sorted(p for p in paths if not (img_root / p).is_file())
    assert not missing, "Missing checklist card images:\n" + "\n".join(missing)
