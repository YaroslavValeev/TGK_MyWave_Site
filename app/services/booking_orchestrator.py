from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any, Dict, Tuple

from flask import session

from app.services.openai_service import respond_structured
from app.services.tools import get_available_slots, get_capacity, book_slot


TOOLS_MANIFEST = [
    {
        "type": "function",
        "function": {
            "name": "get_available_slots",
            "description": "Вернуть список слотов на дату",
            "parameters": {
                "type": "object",
                "properties": {"date": {"type": "string", "description": "YYYY-MM-DD или 'сегодня/завтра'"}},
                "required": ["date"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_capacity",
            "description": "Получить ёмкость слота",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                },
                "required": ["date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_slot",
            "description": "Забронировать слот",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "time": {"type": "string"},
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                },
                "required": ["date", "time", "name", "phone"],
            },
        },
    },
]


TIME_RE = re.compile(r"^\s*(?:в\s*)?(\d{1,2}):(\d{2})\s*$", re.IGNORECASE)
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
PHONE_RE = re.compile(r"(?:(?:\+7|8)\s*\(?\d{3}\)?[\s-]?\d{3}[\s-]?\d{2}[\s-]?\d{2})")


def _merge_state(state: Dict[str, Any] | None, updates: Dict[str, Any]) -> Dict[str, Any]:
    s = dict(state or {})
    s.update({k: v for k, v in updates.items() if v not in (None, "")})
    return s


def _heuristics(user_text: str, state: Dict[str, Any]) -> Dict[str, Any]:
    """Very light rule-based interpretation as a fallback to the model.
    Returns structure compatible with respond_structured output.
    """
    text = (user_text or "").strip().lower()
    out: Dict[str, Any] = {"intent": "other", "entities": {}, "next_step": state.get("step") or "ask_date"}

    # Combined expressions: сегодня/завтра/послезавтра в HH:MM
    for kw in ("сегодня", "завтра", "послезавтра"):
        m = re.match(rf"^\s*{kw}\s*в\s*(\d{{1,2}}:\d{{2}})\s*$", text)
        if m:
            out["intent"] = "provide_datetime"
            out["entities"]["date"] = kw
            out["entities"]["time"] = m.group(1)
            break

    # Date words
    if text in ("сегодня", "завтра"):
        out["intent"] = "provide_date"
        out["entities"]["date"] = text
    if text == "послезавтра":
        out["intent"] = "provide_date"
        out["entities"]["date"] = text
    # ISO date
    if DATE_RE.match(text):
        out["intent"] = "provide_date"
        out["entities"]["date"] = text
    # Time
    m = TIME_RE.match(text)
    if m:
        h, mm = int(m.group(1)), int(m.group(2))
        if 0 <= h < 24 and 0 <= mm < 60:
            out["intent"] = "provide_time"
            out["entities"]["time"] = f"{h:02d}:{mm:02d}"

    # Phone number
    pm = PHONE_RE.search(text)
    if pm:
        raw = re.sub(r"\D", "", pm.group(0))
        if raw.startswith("8"):
            raw = "7" + raw[1:]
        if not raw.startswith("7"):
            raw = "7" + raw
        if len(raw) == 11:
            out.setdefault("entities", {})["phone"] = "+" + raw

    # Name (very light): "меня зовут Иван", "я Иван"
    nm = re.search(r"меня\s+зовут\s+([А-ЯЁA-Z][а-яёa-z\-]+(?:\s+[А-ЯЁA-Z][а-яёa-z\-]+)?)", text, re.IGNORECASE)
    if nm:
        out.setdefault("entities", {})["name"] = nm.group(1).strip()
    else:
        nm2 = re.match(r"^\s*я\s+([А-ЯЁA-Z][а-яёa-z\-]+)\s*$", text, re.IGNORECASE)
        if nm2:
            out.setdefault("entities", {})["name"] = nm2.group(1).strip()

    # Next step decision
    date_known = out["entities"].get("date") or state.get("date")
    time_known = out["entities"].get("time") or state.get("time")
    phone_known = out["entities"].get("phone") or state.get("phone")
    name_known = out["entities"].get("name") or state.get("name")
    if not date_known:
        out["next_step"] = "ask_date"
    elif not time_known:
        out["next_step"] = "ask_time"
    elif not phone_known:
        out["next_step"] = "ask_phone"
    elif not name_known:
        out["next_step"] = "ask_name"
    else:
        out["next_step"] = "confirm"

    return out


def orchestrate(user_text: str, state: Dict[str, Any] | None = None) -> Tuple[str, Dict[str, Any]]:
    """
    Main entry: interpret user text, update booking_state, optionally call tools.
    Returns (reply_text, updated_state).
    """
    state = dict(state or {})

    # 1) Ask the model for structured interpretation (with tools context)
    model_result = respond_structured(user_text, state=state, tools=TOOLS_MANIFEST)
    if model_result.get("error"):
        model_result = _heuristics(user_text, state)

    # 2) If the model returned tool_calls (function calling), execute them sequentially
    reply_chunks: list[str] = []
    if model_result.get("tool_calls"):
        for call in model_result["tool_calls"]:
            name = call.get("name")
            args = call.get("arguments") or {}
            try:
                if name == "get_available_slots":
                    slots = get_available_slots(args.get("date"))
                    if slots:
                        times = ", ".join(s.get("time") for s in slots)
                        reply_chunks.append(f"Доступные слоты: {times}")
                    else:
                        reply_chunks.append("Нет свободных слотов на выбранную дату.")
                elif name == "get_capacity":
                    cap = get_capacity(args.get("date"), args.get("time"))
                    reply_chunks.append(f"Свободно {cap['free']} из {cap['max']}")
                elif name == "book_slot":
                    res = book_slot(args.get("date"), args.get("time"), args.get("name"), args.get("phone"))
                    if res.get("success"):
                        reply_chunks.append(res.get("confirm_text", "Запись подтверждена."))
                        state["step"] = "done"
                    else:
                        reply_chunks.append(res.get("confirm_text", "Не удалось записать."))
                        state["step"] = "ask_time"
            except Exception as e:
                reply_chunks.append(f"Ошибка при вызове инструмента {name}: {e}")

    # 3) Merge entities from interpretation
    entities = model_result.get("entities") or {}
    updated = _merge_state(state, {
        "step": model_result.get("next_step") or state.get("step") or "ask_date",
        "date": entities.get("date") or state.get("date"),
        "time": entities.get("time") or state.get("time"),
        "name": entities.get("name") or state.get("name"),
        "phone": entities.get("phone") or state.get("phone"),
    })

    # 4) If both date and time known and not booked yet, propose capacity/confirm
    if updated.get("date") and updated.get("time") and updated.get("step") in ("confirm", None):
        try:
            cap = get_capacity(updated["date"], updated["time"])
            if cap["free"] > 0:
                reply_chunks.append(
                    f"Подтвердите запись на {updated['date']} в {updated['time']} (свободно {cap['free']} из {cap['max']})."
                )
                updated["step"] = "confirm"
            else:
                reply_chunks.append("К сожалению, слот уже занят. Выберите другое время.")
                updated["step"] = "ask_time"
        except Exception:
            pass

    # 5) Confirmation handling when user affirms/declines
    if updated.get("step") == "confirm":
        if re.search(r"^(да|подтверждаю|ок|хорошо)$", (user_text or "").strip().lower()):
            if updated.get("date") and updated.get("time") and updated.get("phone") and updated.get("name"):
                try:
                    res = book_slot(updated["date"], updated["time"], updated["name"], updated["phone"])
                    if res.get("success"):
                        reply_chunks.append(res.get("confirm_text", "Запись подтверждена."))
                        updated["step"] = "done"
                    else:
                        reply_chunks.append(res.get("confirm_text", "Не удалось записать."))
                        updated["step"] = "ask_time"
                except Exception as e:
                    reply_chunks.append(f"Не удалось завершить запись: {e}")
            else:
                # request missing fields
                if not updated.get("phone"):
                    updated["step"] = "ask_phone"
                elif not updated.get("name"):
                    updated["step"] = "ask_name"
        elif re.search(r"^(нет|не)$", (user_text or "").strip().lower()):
            updated["step"] = "ask_time"

    # 6) If nothing to say yet, ask next required entity
    if not reply_chunks:
        step = updated.get("step") or "ask_date"
        if step == "ask_date":
            reply_chunks.append("Выберите дату (сегодня/завтра или YYYY-MM-DD).")
        elif step == "ask_time":
            # If date known, offer slots
            try:
                slots = get_available_slots(updated.get("date", "")) if updated.get("date") else []
                if slots:
                    times = ", ".join(s.get("time") for s in slots)
                    reply_chunks.append(f"Доступное время: {times}. Укажите удобное время.")
                else:
                    reply_chunks.append("Укажите удобное время.")
            except Exception:
                reply_chunks.append("Укажите удобное время.")
        elif step == "confirm":
            reply_chunks.append("Подтвердите запись (да/нет).")
        elif step == "ask_phone":
            reply_chunks.append("Укажите номер телефона в формате +7XXXXXXXXXX или 8XXXXXXXXXX.")
        elif step == "ask_name":
            reply_chunks.append("Как вас зовут?")

    return (" ".join(reply_chunks).strip(), updated)
