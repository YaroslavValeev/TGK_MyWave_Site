"""Parse KB v2 markdown files: YAML front matter + structured sections."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Tuple

import yaml

from app.services.kb_chat.models import KBDocument

SECTION_ALIASES = {
    "когда использовать": "triggers_section",
    "короткий ответ": "short_answer",
    "подробный ответ": "detailed_answer",
    "кому подходит": "audience",
    "кому подходит / сценарий": "audience",
    "что делать дальше": "next_steps",
    "не говорить": "dont_say_section",
    "cta": "cta_text",
    "тестовые вопросы": "test_questions_section",
    "источники": "sources_section",
}


def split_front_matter(text: str) -> Tuple[dict, str]:
    metadata: dict = {}
    body = text
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            meta_block = parts[1].strip()
            body = parts[2].strip()
            loaded = yaml.safe_load(meta_block)
            metadata = loaded if isinstance(loaded, dict) else {}
    return metadata, body


def _parse_bullet_list(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("- "):
            items.append(line[2:].strip())
        elif line.startswith("* "):
            items.append(line[2:].strip())
        elif re.match(r"^Q:\s*", line, re.I):
            items.append(re.sub(r"^Q:\s*", "", line, flags=re.I).strip())
    return items


def _split_sections(body: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_key = "_intro"
    current_lines: list[str] = []

    for line in body.splitlines():
        heading = re.match(r"^##\s+(.+)$", line.strip())
        if heading:
            sections[current_key] = "\n".join(current_lines).strip()
            title = heading.group(1).strip().lower()
            current_key = SECTION_ALIASES.get(title, title.replace(" ", "_"))
            current_lines = []
        else:
            current_lines.append(line)

    sections[current_key] = "\n".join(current_lines).strip()
    return sections


def parse_kb_file(path: Path) -> KBDocument | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    metadata, body = split_front_matter(text)
    sections = _split_sections(body)

    triggers = _parse_bullet_list(sections.get("triggers_section", ""))
    test_questions = _parse_bullet_list(sections.get("test_questions_section", ""))
    dont_say = _parse_bullet_list(sections.get("dont_say_section", ""))

    category = str(metadata.get("category") or path.parent.name)
    doc_id = str(metadata.get("id") or path.stem)

    return KBDocument(
        id=doc_id,
        title=str(metadata.get("title") or doc_id),
        category=category,
        priority=str(metadata.get("priority") or "normal"),
        cta_type=str(metadata.get("cta_type") or "none"),
        updated_at=str(metadata.get("updated_at") or ""),
        path=path,
        triggers=triggers,
        short_answer=sections.get("short_answer", "").strip(),
        detailed_answer=sections.get("detailed_answer", "").strip(),
        dont_say=dont_say,
        cta_text=sections.get("cta_text", "").strip(),
        test_questions=test_questions,
        raw_body=body,
    )
