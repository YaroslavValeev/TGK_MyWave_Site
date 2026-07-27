"""CTA types and routing rules for KB v2 chat."""
from __future__ import annotations

CTA_BOOKING_BOAT = "booking_boat"
CTA_BOOKING_GYM = "booking_gym"
CTA_BOOKING_CHOOSE = "booking_choose"
CTA_CAMP_APPLY = "camp_apply"
CTA_COACH_APPLY = "coach_apply"
CTA_CONSULTING_APPLY = "consulting_apply"
CTA_PROJECT_CHALLENGE = "project_challenge"
CTA_PROJECT_SAFARI = "project_safari"
CTA_PROJECT_RUZA_APPLY = "project_ruza_apply"
CTA_SOCIAL_APPLY = "social_apply"
CTA_CONTACTS = "contacts"
CTA_NONE = "none"

VALID_CTA_TYPES = frozenset({
    CTA_BOOKING_BOAT,
    CTA_BOOKING_GYM,
    CTA_BOOKING_CHOOSE,
    CTA_CAMP_APPLY,
    CTA_COACH_APPLY,
    CTA_CONSULTING_APPLY,
    CTA_PROJECT_CHALLENGE,
    CTA_PROJECT_SAFARI,
    CTA_PROJECT_RUZA_APPLY,
    CTA_SOCIAL_APPLY,
    CTA_CONTACTS,
    CTA_NONE,
})

_BOAT_MARKERS = ("катер", "катере", "на катере", "на воде", "boat", "сет")
_GYM_MARKERS = ("зал", "зале", "в зал", "помещен", "gym", "тренировк")

_WHAT_TO_BRING_TRIGGERS = (
    "что взять",
    "что нужно с собой",
    "что брать с собой",
    "нужно брать",
)

_PRICE_TRIGGERS = (
    "сколько стоит",
    "стоимость",
    "цена",
    "сколько стоит",
    "прайс",
)

_PURPOSE_TRIGGERS = (
    "для чего",
    "зачем",
    "какая польза",
    "в чем польза",
    "в чём польза",
    "чем полез",
    "зачем нужн",
    "для чего нужн",
    "смысл занят",
    "зачем занят",
)

_BOOKING_TRIGGERS = (
    "как записаться",
    "как записат",
    "как забронировать",
    "как попасть на трениров",
    "как попасть на катер",
    "как попасть в зал",
    "хочу записаться",
    "записаться на",
)

_BOOKING_EXPLICIT_BOAT = ("на катер", "катер", "катере", "на воде", "сет")
_BOOKING_EXPLICIT_GYM = ("в зал", "зал", "зале", "тренировк")

_WAKE_CHALLENGE_MARKERS = (
    "wake challenge",
    "wakesurf challenge",
    "вейк челлендж",
    "вейкчеллендж",
    "челлендж mywave",
    "wsc2025",
    "wsc 2025",
)

_EXTERNAL_CHAMPIONSHIP_MARKERS = (
    "чемпионат россии",
    "чемпионат рф",
    "чемпионате россии",
    "чемпионате рф",
    "на чемпионат",
)


def detect_service_location(text_lc: str, mw_chat_context: dict | None = None) -> str | None:
    """Return 'boat', 'gym', or None."""
    if mw_chat_context and isinstance(mw_chat_context, dict):
        sid = str(mw_chat_context.get("id") or "").lower().strip()
        if sid == "boat":
            return "boat"
        if sid == "gym":
            return "gym"
        title_lc = str(mw_chat_context.get("title") or "").lower()
        if "катер" in title_lc:
            return "boat"
        if "зал" in title_lc:
            return "gym"

    if any(m in text_lc for m in _BOAT_MARKERS):
        return "boat"
    if any(m in text_lc for m in _GYM_MARKERS):
        return "gym"
    return None


def is_what_to_bring_question(text_lc: str) -> bool:
    return any(t in text_lc for t in _WHAT_TO_BRING_TRIGGERS)


def is_price_question(text_lc: str) -> bool:
    return any(t in text_lc for t in _PRICE_TRIGGERS)


def is_purpose_question(text_lc: str) -> bool:
    """Why / benefits intent (not packing list, not price)."""
    if is_what_to_bring_question(text_lc) or is_price_question(text_lc):
        return False
    return any(t in text_lc for t in _PURPOSE_TRIGGERS)


def is_wake_challenge_question(text_lc: str) -> bool:
    return any(m in text_lc for m in _WAKE_CHALLENGE_MARKERS)


def is_external_championship_question(text_lc: str) -> bool:
    """Official championship / federation starts — not Wake Challenge."""
    if is_wake_challenge_question(text_lc):
        return False
    if any(m in text_lc for m in _EXTERNAL_CHAMPIONSHIP_MARKERS):
        return True
    # Generic «чемпионат» without MyWave challenge wording.
    if "чемпионат" in text_lc:
        return True
    return False


def is_booking_how_question(text_lc: str) -> bool:
    if not any(t in text_lc for t in _BOOKING_TRIGGERS):
        return False
    if "отмен" in text_lc or "перенос" in text_lc or "оплат" in text_lc:
        return False
    return True


def needs_booking_disambiguation(text_lc: str, mw_chat_context: dict | None = None) -> bool:
    if not is_booking_how_question(text_lc):
        return False
    if detect_service_location(text_lc, mw_chat_context):
        return False
    if any(m in text_lc for m in _BOOKING_EXPLICIT_BOAT):
        return False
    if any(m in text_lc for m in _BOOKING_EXPLICIT_GYM):
        return False
    return True
