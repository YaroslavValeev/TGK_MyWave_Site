"""Public impact stats for Social Mission widget (anonymized)."""

from __future__ import annotations

from typing import Any, Dict, Optional

from app.config.social_features import is_social_public_stats_enabled


def get_public_social_stats() -> Optional[Dict[str, Any]]:
    """
    Returns anonymized counters for home widget.
    When stats flag is OFF, returns None (widget shows text-only manifest).
  """
    if not is_social_public_stats_enabled():
        return None
    # MVP: static anonymized placeholders until Social_Impact sheet batch is wired.
    return {
        "sessions_completed": 0,
        "applications_received": 0,
        "label_sessions": "социальных тренировок проведено",
        "label_applications": "заявок принято",
    }
