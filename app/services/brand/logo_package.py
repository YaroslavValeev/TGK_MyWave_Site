"""Build downloadable MyWave logo package ZIP."""

from __future__ import annotations

import io
import zipfile
from pathlib import Path
from typing import Iterable, Tuple

PACKAGE_DIR = Path("static/images/logotip_MyWave/MyWave_logo_package_brand_turquoise")

# Практичный набор для партнёров: master + превью + PDF для печати.
INCLUDE_DIRS = ("01_master", "04_previews", "02_print_outdoor")
INCLUDE_ROOT_FILES = ("README.md",)

EXCLUDE_SUFFIXES = {".mov", ".webm", ".mp4", ".tif", ".eps"}
EXCLUDE_PARTS = ("8192px", "6000px_300dpi", "4096px.eps")


def _project_root() -> Path:
    from flask import current_app

    return Path(current_app.root_path).parent


def _should_include(path: Path) -> bool:
    name = path.name.lower()
    if path.suffix.lower() in EXCLUDE_SUFFIXES:
        return False
    lowered = name
    for part in EXCLUDE_PARTS:
        if part.lower() in lowered:
            return False
    return True


def iter_logo_package_files() -> Iterable[Tuple[Path, str]]:
    """Yield (absolute_path, archive_name) pairs."""
    root = _project_root() / PACKAGE_DIR
    if not root.is_dir():
        return

    for filename in INCLUDE_ROOT_FILES:
        file_path = root / filename
        if file_path.is_file():
            yield file_path, filename

    for subdir in INCLUDE_DIRS:
        dir_path = root / subdir
        if not dir_path.is_dir():
            continue
        for file_path in sorted(dir_path.rglob("*")):
            if not file_path.is_file() or not _should_include(file_path):
                continue
            arcname = f"MyWave_logo_package/{subdir}/{file_path.relative_to(dir_path).as_posix()}"
            yield file_path, arcname


def build_logo_package_zip() -> io.BytesIO:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        count = 0
        for file_path, arcname in iter_logo_package_files():
            zf.write(file_path, arcname)
            count += 1
        if count == 0:
            raise FileNotFoundError("logo_package_empty")
        readme = (
            "MyWave Logo Package\n"
            "Brand turquoise: #35C0CD\n"
            "See README.md inside the package folder on the site.\n"
        )
        zf.writestr("MyWave_logo_package/README.txt", readme)
    buffer.seek(0)
    return buffer
