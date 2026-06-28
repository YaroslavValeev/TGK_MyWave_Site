# Social manual assign — Admin workflow spec (no UI)

**Status:** SPEC ONLY — no admin UI in PR56/PR68  
**API:** existing `POST /api/social/sessions/assign`, `PATCH|POST .../sessions/<id>/status`  
**Auth:** `X-Admin-Token` + `SOCIAL_BOOKING_ENABLED=true`

---

## 1. List view (future admin UI)

| Filter | Values |
|--------|--------|
| status | `new`, `review`, `approved`, `scheduled` |
| source | optional |
| date range | `created_at` |

Data source: Google Sheets tab `Social_Applications` (read-only list in UI; writes only via API).

---

## 2. Assign session action

**Trigger:** operator selects application in assignable status (`new` / `review` / `approved`).

**Form fields:**

| Field | Required | Maps to API |
|-------|----------|-------------|
| session_date | yes | `session_date` (ISO date) |
| session_time | yes | `session_time` (HH:MM) |
| location | yes | `location` |
| coach | no | `coach` |
| service_type | no | `service_type` |
| notes | no | `notes` (Sheets only — **not** in Telegram) |
| assigned_by | yes | `assigned_by` (operator id/name) |

**Confirmation:** explicit dialog — «Назначить сессию для {application_id}?»

**API call:**

```http
POST /api/social/sessions/assign
X-Admin-Token: <secret>
Content-Type: application/json

{
  "application_id": "soc_app_...",
  "session_date": "2026-07-15",
  "session_time": "10:00",
  "location": "Зал MyWave",
  "coach": "Иван",
  "service_type": "wake",
  "notes": "внутренний комментарий",
  "assigned_by": "admin_maria"
}
```

**Success (201):** show `session_id`, new status `scheduled`, link to audit history.

**Side effects (server):**

1. Row in `Social_Sessions`
2. `Social_Applications.status` → `scheduled`
3. Rows in `Social_Audit_Log` (assign + status change)
4. Sanitized Telegram (IDs, date, time, location, status — no health/PII)

---

## 3. Session status transitions

| From | To | API |
|------|-----|-----|
| scheduled | completed | `PATCH /api/social/sessions/<session_id>/status` |
| scheduled | cancelled | same |

---

## 4. Audit trail per application

Display `Social_Audit_Log` rows where `application_id` matches. Fields: `timestamp`, `actor`, `action`, `payload_summary`.

---

## 5. Out of scope (this spec)

- Full admin UI implementation
- Auto calendar / booking from public form
- Editing `health_notes` from admin
- Public stats (`SOCIAL_PUBLIC_STATS_ENABLED`)

---

## 6. Security reminders

- Assign endpoints: 401 without valid token (auth before validation)
- `SOCIAL_BOOKING_ENABLED=false` → assign returns 503
- Telegram templates must not include `health_notes`, diagnosis, parent contact details in session-scheduled message
