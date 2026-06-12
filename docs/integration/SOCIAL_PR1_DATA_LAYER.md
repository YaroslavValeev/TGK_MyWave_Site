# Social PR-1 — Data Layer + Feature Flags

**GM approval:** `APPROVED: PR Social-1 — Data layer + feature flags`  
**Date:** 2026-06-12  
**Production:** no deploy, no `.env` changes, all flags default OFF

---

## Affected files

| File | Role |
|------|------|
| `app/config/social_features.py` | Feature flags (default OFF) |
| `app/services/social_schema.py` | Sheets header contracts + validation |
| `app/services/social_store.py` | Application validation, row build, Sheets append |
| `config.py` | Sheet name config keys (no flags ON) |
| `env.example` | Documented social flags (commented) |
| `tests/unit/test_social_features.py` | Flag tests |
| `tests/unit/test_social_store.py` | Store/validation/privacy tests |
| `tests/conftest.py` | Force social flags OFF in CI |

**Not added (Social-2+):** `app/routes/social.py`, templates, JS, booking, Telegram send.

---

## Feature flags (default OFF)

```text
SOCIAL_MODULE_ENABLED=false
SOCIAL_WIDGET_ENABLED=false
SOCIAL_APPLICATIONS_ENABLED=false
SOCIAL_PUBLIC_STATS_ENABLED=false
SOCIAL_ADMIN_NOTIFICATIONS_ENABLED=false
```

Child flags require `SOCIAL_MODULE_ENABLED=1`.

---

## Sheets headers contract

### `Social_Applications`

`application_id`, `created_at`, `updated_at`, `status`, `parent_name`, `parent_phone`, `parent_email`, `child_first_name`, `child_age`, `city`, `preferred_contact`, `telegram_username`, `health_notes`, `motivation_text`, `consent_personal_data`, `consent_training`, `consent_media`, `consent_version`, `source`, `ip_hash`, `assigned_admin`, `booking_id`, `internal_notes`

### `Social_Sessions`

`session_id`, `application_id`, `scheduled_date`, `scheduled_time`, `service`, `booking_id`, `calendar_event_id`, `status`, `created_at`, `created_by`

### `Social_Impact`

`metric_key`, `metric_value`, `period`, `updated_at`

### `Social_Audit_Log`

`event_id`, `timestamp`, `actor`, `action`, `application_id`, `payload_summary`

Validation: `validate_sheet_headers()`, `validate_all_social_sheet_contracts()`.

---

## Test command

```bash
python -m pytest tests/unit/test_social_features.py tests/unit/test_social_store.py -q
```

---

## Statements

| Statement | Answer |
|-----------|--------|
| Production changes | **No** |
| Booking logic change | **No** |
| Auto slot occupation | **No** — forbidden fields rejected (`date`, `time`, `slot`, …) |
| Public `/social` | **No** |
| Telegram production send | **No** — preview helper only for contract tests |
| Privacy | `sanitize_application_for_public()` excludes names, contacts, health |

---

## Docs-only PR (EVENTS-0 / SOCIAL-0)

Prior packages:

```text
docs/integration/EVENTS_COMPETITIONS_PARSER_DISPLAY_AUDIT.md
docs/integration/MYWAVE_SOCIAL_MISSION_IMPLEMENTATION_PACKAGE.md
```

```text
Docs-only PR: yes
Runtime code changed in those commits: no
Production deploy required: no
```

Social-1 adds runtime code only as listed above — still **no production deploy** until GM opens a window.
