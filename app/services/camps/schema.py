"""Camp domain enums and override field contract."""

from __future__ import annotations

SOURCE_SYSTEMS = frozenset({"mywavetour", "owner", "manual", "partner"})
SPORTS = frozenset({"wakesurf", "wakeboard", "mixed"})
LEVELS = frozenset({"beginner", "intermediate", "advanced", "pro", "all_levels"})
ORGANIZER_TYPES = frozenset({"owner", "partner", "external"})
CONTENT_RIGHTS = frozenset({"owned", "partner_allowed", "unknown", "restricted"})
PUBLICATION_STATUSES = frozenset({
    "draft",
    "pending_review",
    "published",
    "hidden",
    "archived",
    "cancelled",
    "possible_duplicate",
})
AVAILABILITY_STATUSES = frozenset({
    "available",
    "few_spots",
    "sold_out",
    "waitlist",
    "unknown",
})

# Fields that admin may override; sync must not overwrite non-null override keys.
SITE_OVERRIDE_FIELDS = (
    "title",
    "seo_title",
    "seo_description",
    "seo_h1",
    "description",
    "short_description",
    "cover_image_url",
    "gallery",
    "booking_url",
    "lead_form_enabled",
    "priority",
    "is_featured",
    "publication_status",
    "robots_index",
    "why_recommend",
)

PUBLICATION_STATUS_LABELS = {
    "draft": "Черновик",
    "pending_review": "На модерации",
    "published": "Опубликован",
    "hidden": "Скрыт",
    "archived": "Архив",
    "cancelled": "Отменён",
    "possible_duplicate": "Возможный дубль",
}

SPORT_LABELS = {
    "wakesurf": "Вейксерф",
    "wakeboard": "Вейкборд",
    "mixed": "Вейксерф + вейкборд",
}

SOURCE_BADGE_LABELS = {
    "owner": "MyWave Camp",
    "manual": "MyWave Camp",
    "partner": "Партнёрский",
    "mywavetour": "Из MyWaveTour",
}

CONTENT_RIGHTS_LABELS = {
    "owned": "Права MyWave",
    "partner_allowed": "Права условно подтверждены источником",
    "unknown": "Права не подтверждены — требуется модерация",
    "restricted": "Права ограничены",
}

TOUR_PUBLICATION_STATUS_LABELS = {
    "published": "Опубликован в Tour",
    "hidden": "Скрыт в Tour",
    "archived": "Архив в Tour",
    "cancelled": "Отменён в Tour (резерв)",
}
