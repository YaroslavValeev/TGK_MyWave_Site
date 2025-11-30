import io
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MD_EXTS = ['.md']

def find_md_files(root):
    for p in root.rglob('*.md'):
        # skip hidden and node_modules if present
        if 'node_modules' in p.parts:
            continue
        yield p

heading_re = re.compile(r'^(#{1,6})\s*(.*)$')
emph_heading_re = re.compile(r'^[ \t]*([*_]{1,2})(.+?)\1[ \t]*$')
code_fence_re = re.compile(r'^(```+)(.*)')

modified_files = []
summary = {
    'files_scanned':0,
    'files_modified':0,
    'headings_fixed':0,
    'trailing_spaces_removed':0,
    'code_fences_fixed':0,
    'duplicate_headings_fixed':0,
    'emph_headings_fixed':0,
}

for md in find_md_files(ROOT):
    summary['files_scanned'] += 1
    text = md.read_text(encoding='utf-8')
    lines = text.splitlines()
    orig_lines = list(lines)
    changed = False

    # Remove trailing spaces
    for i,l in enumerate(lines):
        if l.rstrip('\r\n') != l:
            # shouldn't happen
            pass
        if l.endswith(' '):
            lines[i] = l.rstrip(' ')
            summary['trailing_spaces_removed'] += 1
            changed = True

    # Ensure blank lines around headings and code fences; fix code fences without language
    new_lines = []
    in_code = False
    prev_heading_level = None
    seen_headings = set()

    i = 0
    while i < len(lines):
        l = lines[i]
        # code fence handling
        mcf = code_fence_re.match(l)
        if mcf:
            fence, lang = mcf.group(1), mcf.group(2).strip()
            # ensure a blank line before code fence
            if new_lines and new_lines[-1].strip() != '':
                new_lines.append('')
                changed = True
            # if no language, add 'text'
            if lang == '':
                l = f"{fence}text"
                summary['code_fences_fixed'] += 1
                changed = True
            new_lines.append(l)
            i += 1
            # copy until closing fence
            while i < len(lines):
                new_lines.append(lines[i])
                if code_fence_re.match(lines[i]):
                    break
                i += 1
            # ensure blank line after code fence
            if i+1 < len(lines) and lines[i+1].strip() != '':
                new_lines.append('')
                changed = True
            i += 1
            continue

        # emphasis used as heading
        me = emph_heading_re.match(l)
        if me:
            inner = me.group(2).strip()
            # convert to a level-2 heading
            new_h = '## ' + inner
            new_lines.append(new_h)
            summary['emph_headings_fixed'] += 1
            changed = True
            prev_heading_level = 2
            i += 1
            # ensure blank line after
            if i < len(lines) and lines[i].strip() != '':
                new_lines.append('')
            continue

        # heading handling
        mh = heading_re.match(l)
        if mh:
            level = len(mh.group(1))
            text_h = mh.group(2).strip()
            # heading increment fix
            if prev_heading_level is not None and level > prev_heading_level + 1:
                new_level = prev_heading_level + 1
                l = ('#' * new_level) + ' ' + text_h
                summary['headings_fixed'] += 1
                changed = True
                level = new_level
            # ensure blank line before heading
            if new_lines and new_lines[-1].strip() != '':
                new_lines.append('')
                changed = True
            # duplicate heading detection
            key = (level, text_h.lower())
            if key in seen_headings:
                # append zero-width space to make it unique but visually same
                text_h = text_h + '\u200B'
                l = ('#' * level) + ' ' + text_h
                summary['duplicate_headings_fixed'] += 1
                changed = True
            seen_headings.add(key)
            new_lines.append(l)
            prev_heading_level = level
            # ensure blank line after heading
            if i+1 < len(lines) and lines[i+1].strip() != '':
                new_lines.append('')
                changed = True
            i += 1
            continue

        # normal line
        new_lines.append(l)
        i += 1

    if changed and new_lines != orig_lines:
        bak = md.with_suffix(md.suffix + '.bak')
        if not bak.exists():
            md.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
            bak.write_text(text, encoding='utf-8')
        else:
            md.write_text('\n'.join(new_lines) + '\n', encoding='utf-8')
        modified_files.append(str(md))
        summary['files_modified'] += 1

# print report
print('Markdown Auto-fix Report')
print('Root:', ROOT)
print('Files scanned:', summary['files_scanned'])
print('Files modified:', summary['files_modified'])
print('Headings fixed (increment):', summary['headings_fixed'])
print('Trailing spaces removed:', summary['trailing_spaces_removed'])
print('Code fences fixed (added language):', summary['code_fences_fixed'])
print('Duplicate headings made unique (zero-width):', summary['duplicate_headings_fixed'])
print('Emphasis-as-heading converted:', summary['emph_headings_fixed'])
if modified_files:
    print('\nModified files:')
    for f in modified_files:
        print(' -', f)
else:
    print('\nNo files were modified.')
