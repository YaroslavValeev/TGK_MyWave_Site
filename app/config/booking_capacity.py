"""Phase 2 booking capacity canon (Owner + TGbotAdmin sign-off)."""

from __future__ import annotations

# Катер: exclusive — один клиент на boat-slot / interval.
BOAT_MAX_CLIENTS_PER_SLOT = 1

# Зал: group — до 4 клиентов на один 90-min gym-slot.
GYM_MAX_CLIENTS_PER_SLOT = 4
