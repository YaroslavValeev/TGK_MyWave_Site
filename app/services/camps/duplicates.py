"""Duplicate detection for camp import."""

from __future__ import annotations

from typing import Optional

from sqlalchemy import and_

from app.database.camp_models import Camp
from app.services.camps.normalize import normalized_title_key


def find_by_source_key(session, source_system: str, external_id: Optional[str]) -> Optional[Camp]:
    if not external_id:
        return None
    return (
        session.query(Camp)
        .filter(Camp.source_system == source_system, Camp.external_id == external_id)
        .one_or_none()
    )


def find_possible_duplicate(session, camp: dict) -> Optional[Camp]:
    title_key = camp.get("normalized_title_key") or normalized_title_key(camp.get("title", ""))
    if not title_key:
        return None
    q = session.query(Camp).filter(
        Camp.country == camp.get("country"),
        Camp.start_date == camp.get("start_date"),
        Camp.organizer_name == camp.get("organizer_name"),
        Camp.sport == camp.get("sport"),
    )
    for row in q.limit(20):
        if normalized_title_key(row.title) == title_key:
            return row
    return None


def detect_duplicates(session, camp: dict, *, exclude_id: Optional[int] = None) -> Optional[Camp]:
    by_source = find_by_source_key(session, camp.get("source_system", ""), camp.get("external_id"))
    if by_source and (exclude_id is None or by_source.id != exclude_id):
        return by_source
    fuzzy = find_possible_duplicate(session, camp)
    if fuzzy and (exclude_id is None or fuzzy.id != exclude_id):
        if fuzzy.source_system != camp.get("source_system") or fuzzy.external_id != camp.get("external_id"):
            return fuzzy
    return None
