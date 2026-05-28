# Канон длительности записи (Owner). Не смешивать gym и boat.
# Катер: один «сет» = 25 мин катание + 5 мин тех. (пирс, смена) = 30 мин календарного слота.

BOOKING_DURATION_MINUTES = {
    "gym": 90,
    "boat": 30,  # один сет; несколько сетов = несколько слотов/events
    "camp": 120,
}

BOAT_SET_LABEL = "сет 30 мин (25 мин катание + 5 мин тех.)"

# Calendar / Workouts.location для gym (константа; адрес уточнить у Owner)
GYM_LOCATION_LABEL = "Зал MyWave"
