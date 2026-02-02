import re
from datetime import datetime, timedelta
from typing import Dict, List, Any

from flask import current_app

from app.modules import sheets as sheets_mod


DATE_FMT = "%Y-%m-%d"


def _normalize_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    s = str(date_str).strip().lower()
    today = datetime.now().date()
    if s in ("сегодня", "today"):
        return today.strftime(DATE_FMT)
    if s in ("завтра", "tomorrow"):
        return (today + timedelta(days=1)).strftime(DATE_FMT)
    if s in ("послезавтра", "aftertomorrow"):
        return (today + timedelta(days=2)).strftime(DATE_FMT)
    # через N дней
    import re

    m = re.match(r"^через\s+(\d{1,2})\s*дн", s)
    if m:
        return (today + timedelta(days=int(m.group(1)))).strftime(DATE_FMT)
    # по названию дня недели (рус.)
    weekdays = {
        "понедельник": 0,
        "вторник": 1,
        "сред": 2,  # среда/в среду
        "четверг": 3,
        "пятниц": 4,  # пятница/в пятницу
        "суббот": 5,  # суббота/в субботу
        "воскрес": 6,  # воскресенье/в воскресенье
    }
    for key, idx in weekdays.items():
        if key in s:
            cur = today.weekday()
            delta = (idx - cur) % 7
            delta = delta if delta != 0 else 7
            return (today + timedelta(days=delta)).strftime(DATE_FMT)
    # ДД.ММ.ГГГГ
    try:
        dt = datetime.strptime(s, "%d.%m.%Y")
        return dt.strftime(DATE_FMT)
    except Exception:
        pass

    # YYYY-MM-DD
    try:
        return datetime.strptime(s, DATE_FMT).strftime(DATE_FMT)
    except Exception:
        return None


def _normalize_time(time_str: str | None) -> str | None:
    if not time_str:
        return None
    s = str(time_str).strip()
    # Accept forms like 9:00, 09:00
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*$", s)
    if not m:
        return None
    h = int(m.group(1))
    mm = int(m.group(2))
    if 0 <= h < 24 and 0 <= mm < 60:
        return f"{h:02d}:{mm:02d}"
    return None


def get_available_slots(date: str) -> List[Dict[str, Any]]:
    """Return list of slots {time, available, max_capacity, booked} for a date.

    Uses Schedule + Client_Workouts by default. Workouts for the date override capacity.
    """
    norm_date = _normalize_date(date)
    if not norm_date:
        raise ValueError("Invalid date; expected YYYY-MM-DD or 'сегодня/завтра'")
    # sheets_mod.get_available_slots accepts check_date
    slots = sheets_mod.get_available_slots(norm_date)
    # ensure stable keys and types
    normalized: List[Dict[str, Any]] = []
    for s in slots or []:
        try:
            normalized.append(
                {
                    "time": _normalize_time(s.get("time")) or s.get("time"),
                    "available": int(s.get("available", 0) or 0),
                    "max": int(s.get("max_capacity", s.get("max", 0)) or 0),
                    "booked": int(s.get("booked", 0) or 0),
                }
            )
        except Exception:
            continue
    return normalized


def get_capacity(date: str, time: str) -> Dict[str, int]:
    """Return capacity info for a specific datetime: {free, max}.

    First prefer Workouts(date,time), otherwise fallback to Schedule for that weekday.
    """
    norm_date = _normalize_date(date)
    norm_time = _normalize_time(time)
    if not norm_date or not norm_time:
        raise ValueError("Invalid date/time")

    # Try from Workouts
    workout = sheets_mod.get_workout_by_datetime(norm_date, norm_time)
    if workout:
        max_cap = int(workout.get("max_capacity", 0) or 0)
        participants = sheets_mod.get_workout_participants(workout.get("workout_id"))
        free = max(0, max_cap - int(participants or 0))
        return {"free": free, "max": max_cap}

    # Fallback via Schedule aggregated view
    slots = get_available_slots(norm_date)
    for s in slots:
        if s.get("time") == norm_time:
            return {"free": int(s.get("available", 0)), "max": int(s.get("max", 0))}
    return {"free": 0, "max": 0}


def book_slot(date: str, time: str, name: str, phone: str) -> Dict[str, Any]:
    """Create booking in Client_Workouts and optional calendar sync.

    Returns {success: bool, booking_id?: str, confirm_text: str}
    """
    norm_date = _normalize_date(date)
    norm_time = _normalize_time(time)
    if not norm_date or not norm_time:
        raise ValueError("Invalid date/time for booking")

    ok, msg = sheets_mod.book_slot(norm_date, norm_time, name, phone)
    # sheets_mod.book_slot returns tuple; message can be link or error text
    confirm = (
        msg if ok else (msg or "Не удалось создать запись. Попробуйте другой слот.")
    )
    result: Dict[str, Any] = {"success": bool(ok), "confirm_text": str(confirm)}
    return result
