#!/usr/bin/env python3
"""Generate checklist card WebP illustrations referenced in static/js/checklist.js."""
from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
JS_PATH = ROOT / "static/js/checklist.js"
OUT_ROOT = ROOT / "static/images/Project/Cards/checklist"

PALETTE = {
    "judges": (30, 64, 120),
    "aquatory": (12, 110, 140),
    "participants": (70, 120, 60),
    "organizers": (110, 80, 40),
    "media": (90, 50, 120),
    "viewers": (140, 70, 50),
    "app": (40, 90, 100),
    "partners": (120, 100, 30),
}


def _paths_from_js() -> set[str]:
    text = JS_PATH.read_text(encoding="utf-8")
    return set(re.findall(r"'[^']+': '([^']+\.webp)'", text))


def _color_for(rel: str) -> tuple[int, int, int]:
    folder = rel.split("/", 1)[0]
    return PALETTE.get(folder, (60, 60, 80))


def _render(rel: str, dest: Path) -> None:
    w, h = 640, 400
    base = _color_for(rel)
    img = Image.new("RGB", (w, h), base)
    draw = ImageDraw.Draw(img)
    accent = tuple(min(255, c + 50) for c in base)
    draw.rectangle((24, 24, w - 24, h - 24), outline=accent, width=4)
    label = Path(rel).stem.replace("_", " ")[:42]
    try:
        font = ImageFont.truetype("arial.ttf", 22)
    except Exception:
        font = ImageFont.load_default()
    draw.text((36, 36), label, fill=(245, 245, 245), font=font)
    dest.parent.mkdir(parents=True, exist_ok=True)
    img.save(dest, format="WEBP", quality=82, method=6)


def main() -> None:
    paths = sorted(_paths_from_js())
    if not paths:
        raise SystemExit("No checklist paths found in checklist.js")
    created = 0
    for rel in paths:
        dest = OUT_ROOT / rel
        if dest.is_file():
            continue
        _render(rel, dest)
        created += 1
    print(f"checklist images: total={len(paths)} created={created} root={OUT_ROOT}")


if __name__ == "__main__":
    main()
