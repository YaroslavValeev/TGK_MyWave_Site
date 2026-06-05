"""Canonical booking grid hours (Owner: sync Site with TGbotAdmin)."""

from datetime import time

# Boat slot starts: 07:00–19:30 MSK, step 30 min (see BOAT_SET_MINUTES)
BOAT_GRID_START = time(7, 0)
BOAT_GRID_END = time(19, 30)
