import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def save_to_db(data: dict) -> bool:
    """Minimal placeholder for saving booking in DB for tests.
    Real implementation should validate input and persist to DB.
    """
    # Simulate a DB save
    logger.debug("save_to_db called with %s", data)
    return True


def create_booking(payload: dict) -> dict:
    """Create a booking record.
    Returns a dict with success flag and optionally id.
    """
    if not isinstance(payload, dict) or not payload.get('name'):
        return {'success': False, 'error': 'invalid_payload'}
    saved = save_to_db(payload)
    return {'success': bool(saved)}
