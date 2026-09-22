"""Club Box mode flags (packaging / architecture gates)."""

from __future__ import annotations

import os

_TRUTHY = frozenset({"1", "true", "yes", "on"})


def is_club_box_mode() -> bool:
    """When enabled, legacy booking writers outside the gateway pipeline are blocked."""
    return os.environ.get("CLUB_BOX_MODE", "0").strip().lower() in _TRUTHY
