"""Camp validation before upsert."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple

from app.services.camps.schema import (
    AVAILABILITY_STATUSES,
    CONTENT_RIGHTS,
    LEVELS,
    ORGANIZER_TYPES,
    PUBLICATION_STATUSES,
    SOURCE_SYSTEMS,
    SPORTS,
)


def validate_camp(camp: Dict[str, Any]) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not str(camp.get("title") or "").strip():
        errors.append("title_required")
    if not str(camp.get("slug") or "").strip():
        errors.append("slug_required")
    if camp.get("source_system") not in SOURCE_SYSTEMS:
        errors.append("invalid_source_system")
    if camp.get("sport") not in SPORTS:
        errors.append("invalid_sport")
    if camp.get("level") not in LEVELS:
        errors.append("invalid_level")
    if camp.get("organizer_type") and camp.get("organizer_type") not in ORGANIZER_TYPES:
        errors.append("invalid_organizer_type")
    if camp.get("content_rights_status") and camp.get("content_rights_status") not in CONTENT_RIGHTS:
        errors.append("invalid_content_rights")
    pub = camp.get("publication_status")
    if pub and pub not in PUBLICATION_STATUSES:
        errors.append("invalid_publication_status")
    avail = camp.get("availability_status")
    if avail and avail not in AVAILABILITY_STATUSES:
        errors.append("invalid_availability_status")
    start = camp.get("start_date")
    end = camp.get("end_date")
    if start and end and end < start:
        errors.append("end_before_start")
    return (len(errors) == 0, errors)
