"""
Подсказки для LLM по контексту страницы / выбранной услуги (зал vs катер, раздел сайта).

Клиент передаёт context в POST /chat/api; booking.js вызывает syncChatContextFromBooking(serviceType, title).
Сессия хранит mw_chat_context: entry, kind, id, title — без PII.
"""

from __future__ import annotations

from typing import Any


def format_mw_chat_context_for_prompt(raw: dict[str, Any] | None) -> str:
    """
    Возвращает короткий блок правил на русском для system/instructions.
    Если контекста нет — пустая строка.
    """
    if not raw or not isinstance(raw, dict):
        return ""

    entry = str(raw.get("entry") or "general").lower().strip()
    kind = str(raw.get("kind") or "").lower().strip()
    cid = str(raw.get("id") or "").strip()
    title = (raw.get("title") or "") or ""
    title_s = str(title).strip()
    title_lc = title_s.lower()

    lines: list[str] = ["## Контекст страницы / записи (обязательно учти при ответе):"]

    entry_ru = {
        "general": "общий (раздел не задан)",
        "services": "раздел «Услуги»",
        "shop": "раздел «Товары»",
        "projects": "раздел «Проекты»",
        "home": "главная страница",
    }.get(entry, entry)
    lines.append(f"- Раздел сайта: {entry_ru}.")

    if kind:
        kind_ru = {
            "section": "обзор раздела",
            "service": "конкретная услуга / запись",
            "product": "карточка товара",
            "project": "карточка проекта",
        }.get(kind, kind)
        lines.append(f"- Тип объекта: {kind_ru}.")

    if title_s or cid:
        lines.append(f"- Выбор пользователя: «{title_s or cid}» (код: {cid or '—'}).")

    sid = cid.lower()
    if sid == "gym" or "зал" in title_lc:
        lines.append(
            "Правило для ЗАЛА (занятия в помещении): не предлагай по умолчанию купальник, солнцезащитный крем "
            "и снаряжение для открытой воды, если пользователь явно не спрашивает про улицу/воду. "
            "Уместны: удобная спортивная одежда, полотенце, вода; при необходимости уточни правила конкретного зала "
            "(сменная обувь, душ, раздевалка). Жилеты и доски для катера здесь обычно неуместны."
        )
    elif sid == "boat" or "катер" in title_lc:
        lines.append(
            "Правило для КАТЕРА / выезда на воду: уместны купальная одежда по погоде, полотенце, вода, "
            "защита от солнца на открытом воздухе при необходимости; уточни, что выдаёт база (жилеты, снаряжение)."
        )
    elif sid in ("camp", "coach_triper", "consulting"):
        lines.append(
            f"Услуга с кодом «{sid}»: отвечай в рамках этого формата; не подменяй его общим чек-листом для зала или катера."
        )

    if entry == "shop":
        lines.append(
            "Раздел «Товары»: в первую очередь помогай с выбором товара, доставкой и оплатой; "
            "запись на занятие — только если пользователь сам перешёл к этой теме."
        )
    elif entry == "projects":
        lines.append(
            "Раздел «Проекты»: опирайся на проекты и события MyWave; не смешивай с общими советами без привязки к проекту."
        )
    elif entry == "services" and kind == "section":
        lines.append(
            "Пользователь в обзоре услуг: при вопросе «зал или катер» можно кратко уточнить, о каком формате речь."
        )

    return "\n".join(lines).strip()


def merge_chat_system_prompt(cfg: dict[str, Any], page_context: dict[str, Any] | None) -> str:
    """Базовый CHAT_SYSTEM_PROMPT + блок контекста страницы."""
    base = (cfg.get("CHAT_SYSTEM_PROMPT") if cfg else None) or "You are a helpful assistant."
    base = str(base).strip()
    extra = format_mw_chat_context_for_prompt(page_context)
    if not extra:
        return base
    return f"{base}\n\n{extra}"
