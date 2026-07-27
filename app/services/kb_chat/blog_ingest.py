"""
Авто-инжест блог-постов в KB v2 для чата.

Идея:
- После успешной публикации блога генерируем 1..N KB карточек под интенты.
- Карточки сохраняем в `knowledge_base/chat/blog/` в формате KB v2 markdown.
- В retrieval участвуют только карточки с валидными `Короткий ответ` и `Когда использовать`.

Важно:
- Процесс best-effort: ошибка OpenAI / генерации НЕ должна валить publish pipeline.
- Для единичных/первых постов делаем до `max_sections` чанков по `## Заголовок`.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from flask import current_app

from app.services.kb_chat.parser import split_front_matter
from app.services.openai_service import responses_text_reply


_MD_HEADING_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


def _kb_chat_root() -> Path:
    """
    Корень `knowledge_base/chat`.
    В runtime обычно `current_app.root_path`, но для unit-тестов держим fallback.
    """
    try:
        root = Path(current_app.root_path)
    except Exception:
        root = Path(__file__).resolve().parents[3]
    return root / ".." / "knowledge_base" / "chat"


def _blog_kb_root() -> Path:
    return _kb_chat_root() / "blog"


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in ("1", "true", "yes", "y", "on")


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(str(raw).strip())
    except Exception:
        return default


def extract_blog_sections(content_md: str, *, max_sections: int = 3) -> list[tuple[str, str]]:
    """
    Разбивает markdown на чанки по `##` заголовкам.
    Если заголовков нет — один чанк из всего текста.
    """
    text = str(content_md or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return []

    matches = list(_MD_HEADING_RE.finditer(text))
    if not matches:
        return [("Основное", text[:4000])]

    sections: list[tuple[str, str]] = []
    for idx, m in enumerate(matches):
        title = m.group(1).strip()
        start = m.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        sections.append((title, body[:8000]))
        if len(sections) >= max_sections:
            break

    return sections


def _read_existing_front_matter(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding="utf-8")
        meta, _ = split_front_matter(raw)
        return meta or {}
    except Exception:
        return {}


def _bullets(items: list[str]) -> str:
    return "\n".join([f"- {str(x).strip()}" for x in items if str(x).strip()])


def _render_kb_card_md(
    *,
    doc_id: str,
    title: str,
    category: str,
    priority: str,
    triggers: list[str],
    short_answer: str,
    detailed_answer: str,
    test_questions: list[str],
    dont_say: list[str] | None = None,
    sources: list[str] | None = None,
    blog_checksum: str | None = None,
) -> str:
    # Минимальный набор секций, которые парсер реально сохраняет.
    dont_say = dont_say or []
    sources = sources or []

    updated_at = datetime.utcnow().date().isoformat()

    parts: list[str] = []
    parts.append("---")
    parts.append(f"id: {doc_id}")
    parts.append(f"title: {title}")
    parts.append(f"category: {category}")
    parts.append(f"priority: {priority}")
    parts.append("cta_type: none")
    if blog_checksum:
        parts.append(f"blog_checksum: {blog_checksum}")
    parts.append(f"updated_at: {updated_at}")
    parts.append("---")
    parts.append("")
    parts.append(f"# {title}")

    if triggers:
        parts.append("## Когда использовать")
        parts.append(_bullets(triggers))
        parts.append("")

    parts.append("## Короткий ответ")
    parts.append(str(short_answer).strip())
    parts.append("")

    parts.append("## Подробный ответ")
    parts.append(str(detailed_answer).strip())
    parts.append("")

    if dont_say:
        parts.append("## Не говорить")
        parts.append(_bullets(dont_say))
        parts.append("")

    if test_questions:
        parts.append("## Тестовые вопросы")
        parts.append(_bullets(test_questions))
        parts.append("")

    if sources:
        parts.append("## Источники")
        parts.append(_bullets(sources))
        parts.append("")

    return "\n".join(parts).strip() + "\n"


@dataclass
class BlogCardPayload:
    triggers: list[str]
    test_questions: list[str]
    short_answer: str
    detailed_answer: str
    dont_say: list[str]


def _fallback_card_payload(*, section_title: str, section_body: str) -> BlogCardPayload:
    # Детерминированный режим на случай, если OpenAI недоступен.
    body = section_body.strip()
    first_sentence = re.split(r"[.!?]\s+", body, maxsplit=1)[0].strip()
    short = (first_sentence[:260] + ("…" if len(first_sentence) > 260 else "")).strip()
    if not short:
        short = "Кратко: в статье есть важная информация, которая поможет вам подготовиться."

    detailed = body
    if len(detailed) > 1200:
        detailed = detailed[:1200].rsplit(" ", 1)[0].strip() + "…"

    triggers = [section_title]
    words = re.findall(r"[А-Яа-яA-Za-z0-9]+", section_body.lower())
    key = [w for w in words if len(w) > 4][:8]
    for w in key[:4]:
        triggers.append(w)

    test_questions = [
        f"Что важно знать про «{section_title}»?",
        f"Где в статье есть информация про «{section_title}»?",
    ]

    return BlogCardPayload(
        triggers=list(dict.fromkeys([t for t in triggers if t.strip()])),
        test_questions=test_questions,
        short_answer=short,
        detailed_answer=detailed,
        dont_say=[],
    )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    m = re.search(r"\{.*\}", text, flags=re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except Exception:
        return None


def _generate_card_payload_openai(
    *,
    post_title: str,
    section_title: str,
    section_body: str,
    max_triggers: int = 8,
    max_test_questions: int = 4,
) -> BlogCardPayload:
    instructions = (
        "Ты — редактор и генератор карточек базы знаний для чата MyWave. "
        "Сформируй customer-facing ответ по фрагменту статьи. "
        "Запрещено упоминать внутренние пути и сервисные фразы типа: docs/, BOOKING_*, configs/, "
        "'в чате правила не выдумываем', 'в репозитории не опубликовано', 'не цитируем их как правила'. "
        "Ответ возвращай ТОЛЬКО JSON (без Markdown)."
    )

    prompt = f"""
Статья:
{post_title}

Фрагмент (чанк):
{section_title}

Текст фрагмента:
{section_body}

Верни JSON в точности со схемой:
{{
  "triggers": ["..."],           
  "test_questions": ["..."],    
  "short_answer": "...",         
  "detailed_answer": "...",     
  "dont_say": ["..."]           
}}

Ограничения:
- triggers: 5..{max_triggers} узких фраз (без общих слов типа 'что', 'как' и т.п.)
- test_questions: 2..{max_test_questions} реалистичных вопросов клиента
- short_answer: 1..3 предложения
- detailed_answer: 3..8 предложений
- dont_say: 0..4 фразы, которые нельзя произносить (опционально)
""".strip()

    raw = responses_text_reply(
        prompt,
        instructions=instructions,
        temperature=0.2,
        max_tokens=900,
    )

    payload = _extract_json_object(raw or "")
    if not payload:
        raise RuntimeError("openai_card_payload_json_parse_failed")

    triggers = [str(x).strip() for x in payload.get("triggers") or [] if str(x).strip()]
    test_questions = [
        str(x).strip() for x in payload.get("test_questions") or [] if str(x).strip()
    ]
    short_answer = str(payload.get("short_answer") or "").strip()
    detailed_answer = str(payload.get("detailed_answer") or "").strip()
    dont_say = [str(x).strip() for x in payload.get("dont_say") or [] if str(x).strip()]

    if not short_answer or not detailed_answer:
        raise RuntimeError("openai_card_payload_missing_answers")

    triggers = list(dict.fromkeys(triggers))[:max_triggers]
    test_questions = list(dict.fromkeys(test_questions))[:max_test_questions]

    return BlogCardPayload(
        triggers=triggers,
        test_questions=test_questions,
        short_answer=short_answer,
        detailed_answer=detailed_answer,
        dont_say=dont_say,
    )


def ingest_blog_post_into_chat_kb(post, *, logger=None, force: bool = False) -> dict[str, Any]:
    """
    Пишет карточки в `knowledge_base/chat/blog/` для опубликованной статьи.
    """
    if not _env_bool("BLOG_KB_INGEST_ENABLED", default=True):
        return {"skipped": "BLOG_KB_INGEST_ENABLED=0"}

    max_sections = _env_int("BLOG_KB_INGEST_MAX_SECTIONS", 3)
    max_section_chars = _env_int("BLOG_KB_INGEST_MAX_SECTION_CHARS", 3500)
    category = "blog"
    priority = "low"

    content_md = getattr(post, "content_md", None) or getattr(post, "content_html", None) or ""
    sections = extract_blog_sections(str(content_md), max_sections=max_sections)
    if not sections:
        return {"skipped": "empty_content"}

    kb_root = _blog_kb_root()
    kb_root.mkdir(parents=True, exist_ok=True)

    post_id = str(getattr(post, "id", "") or "").strip() or "unknown"
    slug = str(getattr(post, "slug", "") or "").strip()
    post_title = str(getattr(post, "title", "") or "").strip()
    post_checksum = str(getattr(post, "checksum", "") or "").strip()

    written_paths: list[str] = []
    ingested = 0

    for i, (section_title, section_body) in enumerate(sections):
        section_body = (section_body or "")[:max_section_chars]
        doc_id = f"blog_{post_id}_{i}"
        out_path = kb_root / f"{doc_id}.md"

        if out_path.exists() and not force:
            meta = _read_existing_front_matter(out_path)
            if post_checksum and meta.get("blog_checksum") == post_checksum:
                continue

        sources: list[str] = []
        if slug:
            sources.append(f"/blog/{slug}")

        payload: BlogCardPayload
        use_openai = _env_bool("BLOG_KB_INGEST_USE_OPENAI", default=True)
        try:
            if use_openai:
                payload = _generate_card_payload_openai(
                    post_title=post_title,
                    section_title=section_title,
                    section_body=section_body,
                )
            else:
                raise RuntimeError("openai_disabled")
        except Exception as exc:
            if logger:
                logger.warning("blog_kb_openai_failed", extra={"post_id": post_id, "exc": str(exc)})
            payload = _fallback_card_payload(
                section_title=section_title,
                section_body=section_body,
            )

        md = _render_kb_card_md(
            doc_id=doc_id,
            title=section_title,
            category=category,
            priority=priority,
            triggers=payload.triggers,
            short_answer=payload.short_answer,
            detailed_answer=payload.detailed_answer,
            test_questions=payload.test_questions,
            dont_say=payload.dont_say,
            sources=sources,
            blog_checksum=post_checksum or None,
        )
        out_path.write_text(md, encoding="utf-8")
        written_paths.append(str(out_path))
        ingested += 1

    return {"ingested": ingested, "written_paths": written_paths}

