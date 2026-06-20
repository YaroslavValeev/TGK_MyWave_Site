"""Direct KB replies without OpenAI for high-confidence intents."""
from __future__ import annotations

from app.services.kb_chat.matcher import find_best_match, get_by_stem
from app.services.kb_chat.models import DirectReply
from app.services.kb_chat.routing import (
    CTA_BOOKING_BOAT,
    CTA_BOOKING_CHOOSE,
    CTA_BOOKING_GYM,
    detect_service_location,
    is_booking_how_question,
    is_price_question,
    is_what_to_bring_question,
    needs_booking_disambiguation,
)

# PR50 fallback if MD missing
_FALLBACK_BOAT_BRING = (
    "На катер возьмите: купальник/бордшорты, полотенце, сменную одежду, воду, "
    "солнцезащиту, кепку/очки, телефон в защитном чехле. Если прохладно — уточните гидрокостюм. "
    "Жилет и инвентарь обычно согласуются перед сетом. Приезжайте чуть заранее, чтобы спокойно подготовиться."
)
_FALLBACK_GYM_BRING = (
    "В зал возьмите удобную спортивную одежду, полотенце и воду. "
    "При необходимости — сменную обувь по правилам площадки. "
    "Купальник и солнцезащита для зала обычно не нужны."
)


def _reply_from_doc(doc, *, include_cta: bool = True) -> DirectReply:
    text = doc.short_answer.strip()
    if include_cta and doc.cta_text and doc.cta_type not in ("none", ""):
        if doc.cta_text.lower() not in text.lower():
            text = f"{text} {doc.cta_text}".strip()
    cta = doc.cta_type if doc.cta_type and doc.cta_type != "none" else None
    return DirectReply(text=text, cta_type=cta)


def _try_what_to_bring(text_lc: str, mw_ctx: dict | None) -> DirectReply | None:
    if not is_what_to_bring_question(text_lc):
        return None
    loc = detect_service_location(text_lc, mw_ctx)
    if loc == "boat":
        doc = get_by_stem("boat", "what_to_bring")
        if doc:
            return _reply_from_doc(doc, include_cta=False)
        return DirectReply(text=_FALLBACK_BOAT_BRING)
    if loc == "gym":
        doc = get_by_stem("gym", "what_to_bring")
        if doc:
            return _reply_from_doc(doc, include_cta=False)
        return DirectReply(text=_FALLBACK_GYM_BRING)
    return None


def _try_price(text_lc: str, mw_ctx: dict | None) -> DirectReply | None:
    if not is_price_question(text_lc):
        return None
    loc = detect_service_location(text_lc, mw_ctx)
    if loc == "boat":
        doc = get_by_stem("boat", "prices")
        if doc:
            return _reply_from_doc(doc)
        return DirectReply(
            text="Сет на катере — 10 000 ₽, длительность 25 минут за катером с тренером.",
            cta_type=CTA_BOOKING_BOAT,
        )
    if loc == "gym":
        doc = get_by_stem("gym", "prices")
        if doc:
            return _reply_from_doc(doc)
        return DirectReply(
            text="Тренировка в зале — 3 500 ₽, длительность 1,5 часа.",
            cta_type=CTA_BOOKING_GYM,
        )
    return None


def _try_booking_topic(text_lc: str, mw_ctx: dict | None) -> DirectReply | None:
    if any(w in text_lc for w in ("отмен", "перенос")):
        doc = get_by_stem("booking", "cancellation")
        if doc:
            return _reply_from_doc(doc)
    if "оплат" in text_lc or "сертификат" in text_lc:
        doc = get_by_stem("booking", "payment")
        if doc:
            return _reply_from_doc(doc)
    if "нет нужного времени" in text_lc or "нет слот" in text_lc or (
        "нет" in text_lc and "времен" in text_lc
    ):
        doc = get_by_stem("booking", "cancellation")
        if doc:
            return _reply_from_doc(doc)
    return None


def _try_booking_how(text_lc: str, mw_ctx: dict | None) -> DirectReply | None:
    if needs_booking_disambiguation(text_lc, mw_ctx):
        doc = get_by_stem("booking", "booking_disambiguation")
        text = (
            doc.short_answer
            if doc
            else "Уточните, пожалуйста: вам нужна запись на катер или в зал? Тогда подскажу, как записаться."
        )
        return DirectReply(
            text=text,
            cta_type=CTA_BOOKING_CHOOSE,
            suggestions=["Катер", "Зал"],
        )

    if not is_booking_how_question(text_lc):
        return None

    loc = detect_service_location(text_lc, mw_ctx)
    doc = get_by_stem("booking", "how_to_book")
    if loc == "boat":
        if doc:
            return DirectReply(
                text=doc.short_answer,
                cta_type=CTA_BOOKING_BOAT,
            )
        return DirectReply(
            text="Записаться на катер можно через календарь на сайте: выберите дату и свободный слот.",
            cta_type=CTA_BOOKING_BOAT,
        )
    if loc == "gym":
        if doc:
            return DirectReply(
                text=doc.short_answer,
                cta_type=CTA_BOOKING_GYM,
            )
        return DirectReply(
            text="Записаться в зал можно через календарь на сайте: выберите дату и свободный слот.",
            cta_type=CTA_BOOKING_GYM,
        )
    return None


def try_direct_what_to_bring_reply(
    text_lc: str,
    mw_chat_context: dict | None = None,
) -> DirectReply | None:
    """PR50-compatible what_to_bring direct reply."""
    return _try_what_to_bring(text_lc, mw_chat_context)


def try_direct_kb_reply(
    text_lc: str,
    mw_chat_context: dict | None = None,
) -> DirectReply | None:
    """Unified direct reply: what_to_bring, prices, booking, then generic matcher."""
    for handler in (_try_what_to_bring, _try_price, _try_booking_topic, _try_booking_how):
        result = handler(text_lc, mw_chat_context)
        if result:
            return result

    if is_what_to_bring_question(text_lc) and not detect_service_location(
        text_lc, mw_chat_context
    ):
        return None

    loc = detect_service_location(text_lc, mw_chat_context)
    category = loc if loc in ("boat", "gym", "booking", "brand") else None
    if any(w in text_lc for w in ("контакт", "телефон", "telegram", "связаться")):
        category = "brand"

    doc = find_best_match(text_lc, category=category)
    if doc:
        return _reply_from_doc(doc)

    return None
