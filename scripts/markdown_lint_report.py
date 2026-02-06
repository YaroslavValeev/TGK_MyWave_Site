import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

heading_re = re.compile(r"^(#{1,6})\s*(.*)")
emph_re = re.compile(r"^[ \t]*([*_]{1,2})(.+?)\1[ \t]*$")
code_fence_re = re.compile(r"^(```+)(.*)$")

issues = []
md_files = list(ROOT.rglob("*.md"))
for md in md_files:
    if "node_modules" in md.parts:
        continue
    lines = md.read_text(encoding="utf-8").splitlines()
    prev_level = 0
    headings_seen = {}
    in_code = False
    fence = None
    for i, line in enumerate(lines, start=1):
        # detect code fence open/close
        mcf = code_fence_re.match(line)
        if mcf:
            fence = mcf.group(1)
            lang = mcf.group(2).strip()
            # MD031: fenced code blocks should be surrounded by blank lines
            if i - 2 >= 0:
                prev = lines[i - 2]
                if prev.strip() != "":
                    issues.append(
                        (
                            str(md),
                            i,
                            "MD031",
                            "Code fence should be preceded by a blank line",
                        )
                    )
            if lang == "":
                issues.append(
                    (
                        str(md),
                        i,
                        "MD040",
                        "Fenced code block should have a language specified",
                    )
                )
            # find closing fence
            j = i
            found_close = False
            for j in range(i, len(lines)):
                if lines[j].startswith(fence):
                    found_close = True
                    break
            if found_close:
                # check blank line after
                if j + 1 < len(lines) and lines[j + 1].strip() != "":
                    issues.append(
                        (
                            str(md),
                            j + 1,
                            "MD031",
                            "Code fence should be followed by a blank line",
                        )
                    )
            continue
        # skip inside code blocks (not robust for indented code)
        # heading check
        mh = heading_re.match(line)
        if mh:
            level = len(mh.group(1))
            text = mh.group(2).strip().lower()
            # MD001 heading increment
            if prev_level and level > prev_level + 1:
                issues.append(
                    (
                        str(md),
                        i,
                        "MD001",
                        f"Heading level increased from {prev_level} to {level}",
                    )
                )
            prev_level = level
            key = (level, text)
            if key in headings_seen:
                issues.append(
                    (
                        str(md),
                        i,
                        "MD024",
                        f'Duplicate heading "{mh.group(2).strip()}" previously at line {headings_seen[key]}',
                    )
                )
            else:
                headings_seen[key] = i
            continue
        # emphasis as heading
        me = emph_re.match(line)
        if me:
            issues.append((str(md), i, "MD036", "Emphasis used as heading"))
        # trailing spaces MD009
        if line.endswith(" "):
            issues.append((str(md), i, "MD009", "Trailing spaces"))

# Print report
from collections import defaultdict

by_file = defaultdict(list)
for f, l, code, msg in issues:
    by_file[f].append((l, code, msg))

total = 0
for f in sorted(by_file.keys()):
    print(f"File: {f}")
    for l, code, msg in sorted(by_file[f]):
        print(f"  Line {l}: {code} - {msg}")
        total += 1
    print()

print("Summary:")
print("  Files scanned:", len(md_files))
print("  Issues found:", total)

if total == 0:
    print("No remaining lint issues detected (by this checker).")
else:
    print(
        "Please review the above warnings. For structural fixes (MD001/MD024/MD036) confirm before auto-fix."
    )
