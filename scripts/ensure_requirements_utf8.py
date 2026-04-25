#!/usr/bin/env python3
"""
Приводит requirements.txt в UTF-8 (без BOM).

Если файл был сохранён как UTF-16 (часто после «Сохранить как» в некоторых редакторах),
pip выдаёт: Invalid requirement 'a\\x00i\\x00o\\x00...'.

Запуск из корня репозитория:
  python scripts/ensure_requirements_utf8.py
  python scripts/ensure_requirements_utf8.py path/to/requirements.txt
"""
from __future__ import annotations

import sys
from pathlib import Path


def _read_text(raw: bytes) -> str:
    if raw.startswith(b"\xff\xfe"):
        return raw[2:].decode("utf-16-le")
    if raw.startswith(b"\xfe\xff"):
        return raw[2:].decode("utf-16-be")
    if len(raw) >= 4 and raw[0] and raw[1] == 0 and raw[2] and raw[3] == 0:
        return raw.decode("utf-16-le")
    return raw.decode("utf-8")


def main() -> int:
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("requirements.txt")
    if not target.is_file():
        print(f"Файл не найден: {target}", file=sys.stderr)
        return 1
    raw = target.read_bytes()
    text = _read_text(raw)
    target.write_text(text, encoding="utf-8", newline="\n")
    print(f"OK: {target.resolve()} -> UTF-8, {len(text.splitlines())} строк")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
