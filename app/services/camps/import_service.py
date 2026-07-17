"""MyWaveTour → Site camp import pipeline."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from app.database.camp_models import CampImportLog
from app.database.models import db
from app.services.camps.duplicates import detect_duplicates, find_by_source_key
from app.services.camps.normalize import normalize_tour_camp
from app.services.camps.repository import archive_expired_camps, upsert_camp
from app.services.camps.tour_client import TourCampFetchError, fetch_all_tour_camps
from app.services.camps.validate import validate_camp

logger = logging.getLogger(__name__)


def _failure_message(exc: Exception) -> str:
    if isinstance(exc, TourCampFetchError):
        if exc.kind == "auth" or exc.status_code in (401, 403):
            return f"tour_auth_error_{exc.status_code}"
        if exc.kind == "server" or exc.status_code >= 500:
            return f"tour_server_error_{exc.status_code}"
        if exc.kind == "timeout":
            return "tour_timeout"
        return str(exc)[:500]
    return str(exc)[:500]


def sync_camps_from_tour(*, session=None, updated_since: Optional[datetime] = None) -> Dict[str, Any]:
    session = session or db.session
    log = CampImportLog(source_system="mywavetour", status="running")
    session.add(log)
    session.commit()

    stats: Dict[str, Any] = {
        "fetched": 0,
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "duplicates": 0,
        "errors": 0,
        "archived": 0,
        "content_rights_unknown": 0,
    }
    try:
        raw_items = fetch_all_tour_camps(updated_since=updated_since)
        stats["fetched"] = len(raw_items)

        if not raw_items:
            log.status = "success"
            log.message = "empty_feed"
            log.fetched_count = 0
            log.finished_at = datetime.utcnow()
            log.details_json = stats
            session.commit()
            # Nest stats: LogRecord reserves keys like "created"
            logger.info("camp_sync_empty_feed", extra={"camp_sync": stats})
            return stats

        for raw in raw_items:
            try:
                normalized = normalize_tour_camp(raw)
                ok, errs = validate_camp(normalized)
                if not ok:
                    stats["errors"] += 1
                    logger.warning(
                        "camp_validate_failed",
                        extra={"errors": errs, "external_id": normalized.get("external_id")},
                    )
                    continue

                existing = find_by_source_key(session, "mywavetour", normalized.get("external_id"))
                if existing and existing.sync_hash == normalized.get("sync_hash"):
                    stats["skipped"] += 1
                    continue

                dup = detect_duplicates(session, normalized, exclude_id=existing.id if existing else None)
                if dup and not existing:
                    normalized["publication_status"] = "possible_duplicate"
                    normalized["duplicate_of_id"] = dup.id
                    stats["duplicates"] += 1
                elif not existing:
                    normalized["publication_status"] = "pending_review"
                    normalized["robots_index"] = False
                    if normalized.get("content_rights_status") == "unknown":
                        stats["content_rights_unknown"] += 1

                upsert_camp(session, normalized, existing=existing)
                if existing:
                    stats["updated"] += 1
                else:
                    stats["created"] += 1
                session.flush()
            except Exception as exc:
                stats["errors"] += 1
                logger.exception("camp_upsert_failed: %s", exc)

        stats["archived"] = archive_expired_camps(session)
        log.status = "success"
        log.fetched_count = stats["fetched"]
        log.created_count = stats["created"]
        log.updated_count = stats["updated"]
        log.skipped_count = stats["skipped"]
        log.duplicate_count = stats["duplicates"]
        log.archived_count = stats["archived"]
        log.error_count = stats["errors"]
        log.finished_at = datetime.utcnow()
        log.details_json = stats
        session.commit()
        return stats
    except TourCampFetchError as exc:
        log.status = "failed"
        log.message = _failure_message(exc)
        log.finished_at = datetime.utcnow()
        log.error_count = stats["errors"] + 1
        log.details_json = {**stats, "fetch_error": log.message}
        session.commit()
        logger.error(
            "camp_sync_failed",
            extra={"error": str(exc), "status_code": exc.status_code, "kind": exc.kind},
        )
        raise
    except Exception as exc:
        log.status = "failed"
        log.message = _failure_message(exc)
        log.finished_at = datetime.utcnow()
        log.error_count = stats["errors"] + 1
        log.details_json = {**stats, "fetch_error": log.message}
        session.commit()
        logger.error("camp_sync_failed", extra={"error": str(exc)})
        raise
