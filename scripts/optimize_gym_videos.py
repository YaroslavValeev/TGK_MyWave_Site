#!/usr/bin/env python3
"""Сжатие роликов Gym для карусели на сайте (720p, H.264, без звука)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GYM_DIR = ROOT / "static" / "images" / "Services" / "Gym"
BACKUP_DIR = ROOT / "static" / "images" / "rezerv" / "Services" / "Gym" / "source_full"

FILES = [
    "VudsverhuBatut.mp4",
    "PistolMic.mp4",
    "MarKatSanBatut.mp4",
    "KsuBatut.mp4",
    "KatBatut.mp4",
    "BodyBalanceRom.mp4",
]

# Высота ≤720px, ширина чётная; autorotate по умолчанию (как в телефонных роликах)
SCALE_VF = "scale=-2:720"


def mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)


def optimize_one(src: Path) -> tuple[float, float]:
    tmp = src.with_suffix(".opt.mp4")
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(src),
        "-an",
        "-vf",
        SCALE_VF,
        "-c:v",
        "libx264",
        "-crf",
        "26",
        "-preset",
        "slow",
        "-movflags",
        "+faststart",
        "-pix_fmt",
        "yuv420p",
        str(tmp),
    ]
    subprocess.run(cmd, check=True)
    before = mb(src)
    tmp.replace(src)
    after = mb(src)
    return before, after


def main() -> int:
    if not shutil.which("ffmpeg"):
        print("ffmpeg не найден в PATH", file=sys.stderr)
        return 1

    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    total_before = 0.0
    total_after = 0.0

    for name in FILES:
        path = GYM_DIR / name
        if not path.is_file():
            print(f"SKIP (нет файла): {name}")
            continue

        backup = BACKUP_DIR / name
        if not backup.is_file():
            shutil.copy2(path, backup)
            print(f"backup: {backup.relative_to(ROOT)}")

        source = backup if backup.is_file() else path
        if source != path:
            shutil.copy2(source, path)

        b, a = optimize_one(path)
        total_before += b
        total_after += a
        print(f"OK {name}: {b:.1f} MB -> {a:.1f} MB ({100 * a / b:.0f}% от исходника)")

    print(f"\nИтого: {total_before:.1f} MB -> {total_after:.1f} MB")
    print(f"Оригиналы: {BACKUP_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
