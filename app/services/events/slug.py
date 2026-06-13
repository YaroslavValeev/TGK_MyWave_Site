"""Slug helpers for Events-3 public detail URLs."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, List, Optional

from app.services.events.public_eligibility import is_public_eligible
from app.services.events.schema import NormalizedContentItem

_SLUG_PART_RE = re.compile(r"[^a-z0-9]+")
_EVENT_ID_TAIL_LEN = 8


def event_id_tail(event_id: str, length: int = _EVENT_ID_TAIL_LEN) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]", "", event_id or "")
    if not clean:
        return ""
    return clean[-length:].lower() if len(clean) >= length else clean.lower()


def slugify_title(title: str, max_len: int = 60) -> str:
    text = unicodedata.normalize("NFKD", (title or "").strip())
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = _SLUG_PART_RE.sub("-", text).strip("-")
    if len(text) > max_len:
        text = text[:max_len].rstrip("-")
    return text


def build_public_slug(item: NormalizedContentItem) -> str:
    tail = event_id_tail(item.event_id)
    title_part = slugify_title(item.title)
    if title_part and tail:
        return f"{title_part}-{tail}"
    return tail or slugify_title(item.event_id) or "event"


def parse_slug_tail(slug: str) -> Optional[str]:
    if not slug or "-" not in slug:
        tail = slugify_title(slug)
        return tail if tail and tail.isalnum() else None
    _, tail = slug.rsplit("-", 1)
    tail = (tail or "").strip().lower()
    return tail if tail.isalnum() else None


@dataclass(frozen=True)
class SlugResolveResult:
    item: NormalizedContentItem
    canonical_slug: str
    redirect_required: bool = False


def resolve_item_by_slug(
    slug: str,
    items: List[NormalizedContentItem],
) -> Optional[SlugResolveResult]:
    tail = parse_slug_tail(slug)
    if not tail:
        return None

    matches: List[NormalizedContentItem] = []
    for item in items:
        if not is_public_eligible(item):
            continue
        item_tail = event_id_tail(item.event_id)
        if item_tail == tail or (item.event_id or "").lower().endswith(tail):
            matches.append(item)

    if not matches:
        return None
    if len(matches) > 1:
        matches.sort(key=lambda it: it.event_id)

    item = matches[0]
    canonical = build_public_slug(item)
    return SlugResolveResult(
        item=item,
        canonical_slug=canonical,
        redirect_required=canonical != slug,
    )


def find_public_item_by_event_id(
    event_id: str,
    items: List[NormalizedContentItem],
) -> Optional[NormalizedContentItem]:
    needle = (event_id or "").strip()
    if not needle:
        return None
    for item in items:
        if not is_public_eligible(item):
            continue
        if item.event_id == needle:
            return item
    return None
