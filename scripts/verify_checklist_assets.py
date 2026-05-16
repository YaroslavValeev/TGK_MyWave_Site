#!/usr/bin/env python3
"""Verify checklist checkbox → webp mapping and files on disk."""
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "static/js/checklist.js").read_text(encoding="utf-8")
HTML = (ROOT / "templates/wake_industry/checklist.html").read_text(encoding="utf-8")
BASE = ROOT / "static/images/Project/Cards/checklist"

bg = dict(re.findall(r"'([a-z0-9-]+)':\s*'([^']+\.webp)'", JS))
ids = set(re.findall(r'id="([^"]+)" class="wake-checklist__checkbox"', HTML))

print("checkboxes", len(ids), "mapped", len(bg))
print("missing map", sorted(ids - bg.keys()))
print("extra map", sorted(bg.keys() - ids))
missing = [rel for rel in bg.values() if not (BASE / rel.replace("/", os.sep)).is_file()]
print("missing files", len(missing))
for rel in missing[:10]:
    print(" ", rel)

# Placeholders in repo are ~2–3 KB; final art is usually 40+ KB per file
small = []
for rel in bg.values():
    p = BASE / rel.replace("/", os.sep)
    if p.is_file() and p.stat().st_size < 8000:
        small.append((p.stat().st_size, rel))
if small:
    print("placeholder-sized webp (<8KB):", len(small), "— replace with final illustrations")
