"""
Content type classifier for events/competitions/news (Events-1).

Read-only: does not change blog publishability, parser, or public UI.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from app.services.competitions.visibility import parse_iso_date
from app.services.events.content_types import (
    CLASSIFIER_CONFIDENCE_THRESHOLD,
    CONTENT_TYPES,
    NEEDS_REVIEW_STATUS,
    ContentType,
    EventTrackStatus,
)
from app.services.events.schema import ClassificationResult

_COMPETITION_RE = re.compile(
    r"(соревнован|чемпионат|турнир|этап\b|contest|championship|champ\b|"
    r"world\s+cup|iwwf|wakesurf\s+tour|registration\s+open)",
    re.IGNORECASE,
)
_CAMP_RE = re.compile(
    r"(лагер|кэмп|\bcamp\b|summer\s+camp|интенсив)",
    re.IGNORECASE,
)
_WORKSHOP_RE = re.compile(
    r"(мастер[-\s]?класс|workshop|воркшоп|семинар|тренинг[-\s]?день)",
    re.IGNORECASE,
)
_EVENT_RE = re.compile(
    r"(мероприят|фестивал|open\s+day|день\s+открытых|событие|meetup|"
    r"форум|конференц)",
    re.IGNORECASE,
)
_NEWS_RE = re.compile(
    r"(новост|обзор|итог|результат|интервью|article|news\b)",
    re.IGNORECASE,
)

_SOURCE_COMPETITION = frozenset(
    {"iwwf", "wwa", "wsws", "federation", "tour", "championship"}
)


def _norm_row(row: Mapping[str, Any]) -> Dict[str, Any]:
    return {str(k).strip().lower(): v for k, v in row.items() if k is not None}


def _text_blob(row: Mapping[str, Any]) -> str:
    r = _norm_row(row)
    parts = [
        str(r.get(k) or "")
        for k in (
            "title",
            "raw_title",
            "event_name",
            "summary",
            "excerpt",
            "final_posts",
            "text",
            "raw_content",
            "tags",
            "raw_tags",
        )
    ]
    return " ".join(p.strip() for p in parts if p and str(p).strip())


def _explicit_content_type(row: Mapping[str, Any]) -> Optional[ContentType]:
    raw = str(_norm_row(row).get("content_type") or "").strip().lower()
    if not raw:
        return None
    if raw in CONTENT_TYPES:
        return raw  # type: ignore[return-value]
    return None


def _score_patterns(text: str) -> Dict[ContentType, float]:
    scores: Dict[ContentType, float] = {
        "competition": 0.0,
        "camp": 0.0,
        "workshop": 0.0,
        "event": 0.0,
        "news": 0.0,
    }
    if _COMPETITION_RE.search(text):
        scores["competition"] += 0.45
    if _CAMP_RE.search(text):
        scores["camp"] += 0.45
    if _WORKSHOP_RE.search(text):
        scores["workshop"] += 0.45
    if _EVENT_RE.search(text):
        scores["event"] += 0.35
    if _NEWS_RE.search(text):
        scores["news"] += 0.35
    return scores


def _has_location(row: Mapping[str, Any]) -> bool:
    r = _norm_row(row)
    for key in ("location", "location_name", "city", "country"):
        if str(r.get(key) or "").strip():
            return True
    return False


def _parse_dates(row: Mapping[str, Any]) -> Tuple[Optional[Any], Optional[Any]]:
    r = _norm_row(row)
    start = parse_iso_date(r.get("start_date") or r.get("event_date") or r.get("date"))
    end = parse_iso_date(r.get("end_date")) or start
    return start, end


def _source_type_boost(row: Mapping[str, Any], scores: Dict[ContentType, float]) -> None:
    r = _norm_row(row)
    source_type = str(r.get("source_type") or "").strip().lower()
    source_name = str(r.get("source_name") or "").strip().lower()
    for token in _SOURCE_COMPETITION:
        if token in source_type or token in source_name:
            scores["competition"] += 0.25
            break


def _pick_best_type(scores: Dict[ContentType, float]) -> Tuple[ContentType, float]:
    ordered: List[Tuple[ContentType, float]] = sorted(
        scores.items(), key=lambda x: (-x[1], x[0])
    )
    best_type, best_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0
    # Penalize ambiguity when top two scores are close.
    if best_score > 0 and (best_score - second_score) < 0.1:
        return best_type, max(0.0, best_score - 0.15)
    return best_type, best_score


def _derive_track_status(
    content_type: ContentType,
    confidence: float,
    row: Mapping[str, Any],
    *,
    start_date: Optional[Any],
    needs_review: bool,
) -> EventTrackStatus:
    if needs_review:
        return NEEDS_REVIEW_STATUS

    r = _norm_row(row)
    sheet_status = str(r.get("status") or "").strip().upper()

    if sheet_status == "ARCHIVED":
        return "archived"
    if sheet_status in {"DRAFT", "PARSED"}:
        return sheet_status.lower()  # type: ignore[return-value]

    if content_type == "news":
        if sheet_status in {"READY_TO_PUBLISH", "PUBLISHED"}:
            return "published"
        return "parsed"

    if content_type in {"competition", "event", "camp", "workshop"}:
        if not start_date:
            return NEEDS_REVIEW_STATUS
        if sheet_status == "ACTIVE":
            return "published"
        if sheet_status in {"READY_TO_PUBLISH", "PUBLISHED"}:
            return "published"
        if confidence >= CLASSIFIER_CONFIDENCE_THRESHOLD:
            return "parsed"
        return NEEDS_REVIEW_STATUS

    return "parsed"


def classify_row(
    row: Mapping[str, Any],
    *,
    source_hint: str = "raw_feed",
) -> ClassificationResult:
    """
    Classify a dict row from raw_feed (or similar) without side effects.
    """
    reasons: List[str] = []
    explicit = _explicit_content_type(row)
    start_date, _end_date = _parse_dates(row)
    has_loc = _has_location(row)
    text = _text_blob(row)

    if explicit:
        confidence = 0.92
        content_type = explicit
        reasons.append("explicit_content_type")
        if content_type != "news" and not start_date:
            reasons.append("missing_start_date")
        if content_type != "news" and not has_loc:
            reasons.append("missing_location")
    else:
        scores = _score_patterns(text)
        if start_date:
            scores["competition"] += 0.15
            scores["event"] += 0.15
            scores["camp"] += 0.1
        if has_loc:
            scores["competition"] += 0.1
            scores["event"] += 0.1
        _source_type_boost(row, scores)

        content_type, confidence = _pick_best_type(scores)
        if confidence <= 0:
            content_type = "news"
            confidence = 0.4
            reasons.append("fallback_news")
        else:
            reasons.append(f"heuristic:{content_type}")

        r = _norm_row(row)
        sheet_status = str(r.get("status") or "").strip().upper()
        has_body = bool(str(r.get("text") or r.get("final_posts") or "").strip())
        if content_type == "news" and sheet_status in {"PUBLISHED", "READY_TO_PUBLISH"} and has_body:
            confidence = max(confidence, 0.75)
            reasons.append("publishable_news_row")

    needs_review = False
    if confidence < CLASSIFIER_CONFIDENCE_THRESHOLD:
        needs_review = True
        reasons.append("low_confidence")
    if content_type in {"competition", "event", "camp", "workshop"} and not start_date:
        needs_review = True
        reasons.append("missing_start_date")
    if content_type == "competition" and not (
        _COMPETITION_RE.search(text) or explicit == "competition"
    ):
        if confidence < 0.7:
            needs_review = True
            reasons.append("weak_competition_signal")

    track_status = _derive_track_status(
        content_type,
        confidence,
        row,
        start_date=start_date,
        needs_review=needs_review,
    )
    if track_status == NEEDS_REVIEW_STATUS:
        needs_review = True

    return ClassificationResult(
        content_type=content_type,
        track_status=track_status,
        confidence=min(1.0, confidence),
        needs_review=needs_review,
        reasons=reasons,
        source_hint=source_hint,
    )


def classify_competitions_ticker_row(row: Mapping[str, Any]) -> ClassificationResult:
    """competitions_ticker rows are competitions by contract."""
    r = _norm_row(row)
    start_date, end_date = _parse_dates(row)
    reasons: List[str] = ["source:competitions_ticker"]

    title = str(r.get("event_name") or "").strip()
    needs_review = False
    confidence = 0.95

    if not title:
        needs_review = True
        reasons.append("missing_event_name")
        confidence = 0.3
    if not start_date:
        needs_review = True
        reasons.append("missing_start_date")
        confidence = min(confidence, 0.35)
    if end_date and start_date and end_date < start_date:
        needs_review = True
        reasons.append("invalid_date_range")
        confidence = min(confidence, 0.4)

    status_raw = str(r.get("status") or "").strip().upper()
    if needs_review:
        track_status: EventTrackStatus = NEEDS_REVIEW_STATUS
    elif status_raw == "ACTIVE":
        track_status = "published"
    elif status_raw == "ARCHIVED":
        track_status = "archived"
    else:
        track_status = "parsed"
        reasons.append(f"sheet_status:{status_raw or 'empty'}")

    return ClassificationResult(
        content_type="competition",
        track_status=track_status,
        confidence=confidence,
        needs_review=needs_review,
        reasons=reasons,
        source_hint="competitions_ticker",
    )


def should_route_to_blog_vitrine(result: ClassificationResult) -> bool:
    """
    Events-1 helper for future integration: non-news or needs_review must not
    auto-join blog vitrine when classifier is wired (Events-2+).
    """
    if result.needs_review:
        return False
    if result.content_type != "news":
        return False
    return True
