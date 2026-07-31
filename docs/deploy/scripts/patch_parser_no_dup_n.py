#!/usr/bin/env python3
"""Patch Parser on prod: stop Telethon minting `file (N).ext` in downloads/.

Run on host with code at /opt/bot3/parser-new-bot (or set PARSER_ROOT).
Does NOT delete downloads/; only rewrites download_media helpers.
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ.get("PARSER_ROOT", "/opt/bot3/parser-new-bot")).resolve()

NEW_MEDIA_UTILS_FN = '''
async def download_media(message: Any, download_dir: str = "downloads/") -> tuple[str | None, str | None]:
    """Download media to a stable path; overwrite on re-download (no Telethon ` (N)`)."""
    try:
        if not getattr(message, "media", None):
            return None, None
        os.makedirs(download_dir, exist_ok=True)
        chat = getattr(message, "chat_id", None) or getattr(message, "peer_id", None) or "chat"
        mid = getattr(message, "id", None) or "0"
        # Explicit file path (not a directory) => Telethon overwrites instead of minting (1)/(2).
        target = os.path.join(download_dir, f"tg_{chat}_{mid}")
        path = await message.download_media(file=target)
        if not isinstance(path, str) or not path.strip():
            return None, None
        return path.strip(), media_kind_from_path(path)
    except Exception:
        return None, None
'''

NEW_HELPERS_FN = '''
async def download_media(message: types.Message, download_dir: str = "downloads/") -> bool:
    """Загружает медиа; стабильное имя + overwrite (без ` (N)`)."""
    try:
        if not message.media:
            return False
        os.makedirs(download_dir, exist_ok=True)
        chat = getattr(message, "chat_id", None) or "chat"
        mid = getattr(message, "id", None) or "0"
        file_ext = ""
        if isinstance(message.media, types.MessageMediaPhoto):
            file_ext = ".jpg"
        elif isinstance(message.media, types.MessageMediaDocument):
            file_ext = ""
        target = f"{download_dir.rstrip('/')}/tg_{chat}_{mid}{file_ext}"
        await message.download_media(file=target)
        await asyncio.sleep(config.MEDIA_DOWNLOAD_DELAY)
        return True
    except Exception as e:
        if "cancel" in str(e).lower():
            logger.error(
                f"Ошибка загрузки медиа для сообщения ID {message.id}: {e}",
                exc_info=True,
            )
            return False
        return False
'''

NEW_PARSER_FN = '''
async def download_media(message) -> bool:
    """Загрузка медиа: стабильный путь + overwrite (не directory downloads/)."""
    try:
        if not message.media:
            return False
        import os

        os.makedirs("downloads", exist_ok=True)
        chat = getattr(message, "chat_id", None) or "chat"
        mid = getattr(message, "id", None) or "0"
        target = f"downloads/tg_{chat}_{mid}"
        await message.download_media(file=target)
        await asyncio.sleep(config.MEDIA_DOWNLOAD_DELAY)
        return True
    except Exception as e:
        logger.error(f"Ошибка загрузки медиа: {e}")
        return False
'''


def _patch_media_utils(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = 'async def download_media(message: Any, download_dir: str = "downloads/")'
    idx = text.rfind(anchor)
    if idx < 0:
        if "tg_" in text and "download_media" in text and "file=download_dir" not in text:
            print(f"skip {path}: already looks patched")
            return
        if 'file=download_dir' not in text and 'file="downloads/"' not in text:
            print(f"skip {path}: no directory-mode download_media found")
            return
        raise SystemExit(f"{path}: download_media Any/downloads anchor not found")
    path.write_text(
        text[:idx].rstrip() + "\n\n" + NEW_MEDIA_UTILS_FN.lstrip() + "\n",
        encoding="utf-8",
    )
    print(f"patched {path}")


def _patch_helpers(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "import os" not in text:
        text = text.replace("import asyncio\n", "import asyncio\nimport os\n", 1)
    anchor = (
        'async def download_media(message: types.Message, download_dir: str = "downloads/")'
    )
    idx = text.find(anchor)
    if idx < 0:
        if 'file="downloads/' in text or "file='downloads/" in text:
            raise SystemExit(f"{path}: unexpected download_media shape")
        print(f"skip {path}: download_media not found or already changed")
        return
    path.write_text(
        text[:idx].rstrip() + "\n\n" + NEW_HELPERS_FN.lstrip() + "\n",
        encoding="utf-8",
    )
    print(f"patched {path}")


def _patch_telegram_parser(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    anchor = "async def download_media(message) -> bool:"
    idx = text.find(anchor)
    if idx < 0:
        print(f"skip {path}: local download_media not found")
        return
    if 'file="downloads/"' not in text[idx : idx + 800] and "tg_" in text[idx : idx + 800]:
        print(f"skip {path}: already patched")
        return
    rest = text[idx:]
    end_m = re.search(r"\n(# Пример использования|async def main\()", rest)
    end = idx + end_m.start() if end_m else len(text)
    path.write_text(
        text[:idx].rstrip()
        + "\n\n"
        + NEW_PARSER_FN.lstrip()
        + "\n\n"
        + text[end:].lstrip(),
        encoding="utf-8",
    )
    print(f"patched {path}")


def main() -> int:
    if not ROOT.is_dir():
        print(f"PARSER_ROOT missing: {ROOT}", file=sys.stderr)
        return 2
    _patch_media_utils(ROOT / "utils" / "media_utils.py")
    _patch_helpers(ROOT / "utils" / "helpers.py")
    _patch_telegram_parser(ROOT / "collectors" / "telegram_parser.py")

    bad = []
    for rel in (
        "utils/media_utils.py",
        "utils/helpers.py",
        "collectors/telegram_parser.py",
    ):
        t = (ROOT / rel).read_text(encoding="utf-8")
        if 'file="downloads/"' in t or "file='downloads/'" in t:
            bad.append(f"{rel}: still has file=downloads/")
        if "file=download_dir)" in t or "file=download_dir," in t:
            # allow only if not the call site — check call
            if re.search(r"download_media\(\s*file=download_dir\s*\)", t):
                bad.append(f"{rel}: still has file=download_dir")
    if bad:
        print("VERIFY_FAIL:")
        for b in bad:
            print(" ", b)
        return 1
    print("VERIFY_OK: no directory-mode download_media left in patched files")
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
