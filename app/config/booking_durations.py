# Канон длительности записи (Owner). Не смешивать gym и boat.
# Катер: один «сет» = 25 мин катание + 5 мин тех. (пирс, смена) = 30 мин календарного слота.

BOOKING_DURATION_MINUTES = {
    "gym": 90,
    "boat": 30,  # один сет; Phase 2 multi-set = один continuous event (N×30)
    "camp": 120,
}

# Phase 2 aliases (contract canon — keep in sync with BOOKING_DURATION_MINUTES)
BOAT_SET_MINUTES = BOOKING_DURATION_MINUTES["boat"]
GYM_SLOT_MINUTES = BOOKING_DURATION_MINUTES["gym"]

# Travel buffer между Зал ↔ Катер (hard blocker when Phase 2 buffer flag ON)
TRAINER_TRAVEL_BUFFER_MINUTES = 120

BOAT_SET_LABEL = "сет 30 мин (25 мин катание + 5 мин тех.)"

# Calendar / Workouts.location для gym (Phase 1 production; v2 = «Зал» via booking_venues)
GYM_LOCATION_LABEL = "Зал MyWave"
