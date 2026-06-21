"""Data models for KB v2 chat documents."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class KBDocument:
    id: str
    title: str
    category: str
    priority: str
    cta_type: str
    updated_at: str
    path: Path
    triggers: list[str] = field(default_factory=list)
    short_answer: str = ""
    detailed_answer: str = ""
    dont_say: list[str] = field(default_factory=list)
    cta_text: str = ""
    test_questions: list[str] = field(default_factory=list)
    raw_body: str = ""

    def snippet_text(self) -> str:
        parts = [self.title]
        if self.short_answer:
            parts.append(self.short_answer)
        if self.detailed_answer:
            parts.append(self.detailed_answer)
        return "\n\n".join(parts)


@dataclass
class DirectReply:
    text: str
    cta_type: str | None = None
    suggestions: list[str] | None = None
