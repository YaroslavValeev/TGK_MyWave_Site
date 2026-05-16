#!/usr/bin/env python3
"""Export unique checklist webp paths for design handoff (read-only)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "static/js/checklist.js"
BASE = ROOT / "static/images/Project/Cards/checklist"
OUT = ROOT / "docs/ops/CHECKLIST_ART_FILE_MANIFEST.txt"


def main() -> None:
    js = JS.read_text(encoding="utf-8")
    paths = sorted(set(re.findall(r"'[^']+': '([^']+\.webp)'", js)))
    lines = [
        "# Checklist final art — replace these files in-place (same paths, same names)",
        f"# Unique webp files: {len(paths)}",
        "# Format: relative_path<TAB>size_bytes",
        "",
    ]
    for rel in paths:
        fp = BASE / rel.replace("/", "\\")
        sz = fp.stat().st_size if fp.is_file() else 0
        lines.append(f"{rel}\t{sz}")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(paths)} files)")


if __name__ == "__main__":
    main()
