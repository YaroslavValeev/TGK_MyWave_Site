# Opt-in internal booking API

`create_internal_booking_blueprint(engine, club=..., schema=..., secret=...)`
creates a Flask blueprint at `/api/internal/booking`. It uses the existing Site
SQLAlchemy engine and the migrated ledger from PRs #119/#120. This release does
not register the factory in Site or change Website/Telegram routing. It is an
API component ready for isolated review, not a completed portable Club Box.

The caller supplies the canonical Club Box JSON schema and non-secret club
configuration. Schema and policy validation happen before registration. Supply
the new owner's gateway secret from `.env`/secret manager; minimum 32 characters.
Do not send this secret to browser JavaScript, export it in logs or place it in
club.yaml. Every endpoint requires `X-MyWave-Gateway-Secret`.

## HTTP contract

| Method | Path after prefix | Input | Result |
|---|---|---|---|
| GET | `/health` | Header | Actual ledger query, provider/read/write status |
| GET | `/slots` | `date`, optional `boat_id` | `slots` with start_time/duration_minutes/available |
| POST | `/bookings` | date/time/client_name/client_phone/set_count/internal_id, optional boat_id | record_id/status/raw |
| GET | `/bookings/{id}` | Header | Minimal record, without name/phone |
| PATCH | `/bookings/{id}` | datetime/seance_length, optional boat_id | record_id/status/raw |
| POST | `/bookings/{id}/cancel` | Header | record_id/status |

These input names and the authentication header match the server's static
Telegram Admin contract inventory. The actual bot has not been run against this
API; response consumption, provider enums and duration semantics
still require consumer integration checks. `source`/`use_online` do not activate
an external provider and are not persisted as audit events by this component.

## Policy

- Only internal mode with the external commercial adapter disabled is accepted.
- The booking module must be enabled; there must be unique active boats.
- Dates are in the configured season; local times must lie on the configured
  weekly grid. Every occupied multi-set slot must fit that grid. Sets: 1–10.
- One active boat can be selected implicitly. With multiple boats, boat_id is
  required on creation and slot queries. Moves default to the booking's boat.
- Club timezone is explicit. Ambiguous/nonexistent DST times are rejected.
  A PATCH datetime without offset is interpreted in that configured zone;
  an offset-bearing datetime is converted to it. Windows runtime includes tzdata.
  Past slots, malformed dates, non-minute timestamps and partial occupancy
  durations are rejected. On the wire, `seance_length` is occupied **seconds**,
  including the buffer, matching the actual Telegram client's legacy contract.
  For a 30-minute booking send 1800. Responses also expose `duration_minutes`
  explicitly. Storage and slot-grid calculations continue to use minutes.
  Omitted PATCH duration preserves the existing occupied interval. Partial
  minutes and values such as 30 (seconds, not minutes) are rejected.
- Nonempty schedule overrides are refused until their contract is defined;
  they are never silently ignored. Bad setup must be corrected before startup.
- Creation uses internal_id, then Idempotency-Key, then a deterministic request
  key. A fresh booking after cancellation requires an explicit fresh key.
- Cancellation/reschedule windows come from club configuration. The window is
  checked under the ledger writer lock against the current stored booking.
  Repeated completed move/cancel does not apply a new destructive action.
- Availability is a hint; writes recheck occupancy transactionally. JSON mutation
  bodies above 64 KiB are rejected. Wrong auth returns 401, absent record 404,
  conflict 409, malformed input 400 and storage failure a sanitized 503.

Current idempotent creation retries still need a valid future/configured slot;
after a slot passes or a schedule changes, retrieve the known booking id rather
than replaying creation. This limitation must be considered by consumer retries.

## Activation prerequisites and rollback

Register this blueprint only in a dedicated Club Box runtime or after ALL existing
commercial write paths are redirected or disabled. Merely changing the bot's
gateway URL while Website still writes Calendar/Sheets creates separate ledgers.
Website, Telegram Admin, legacy APIs, optional Club Ops and availability must use
the same writer. This PR deliberately does not claim that integration is done.

When adding it to a Site runtime with global CSRF protection, exempt this specific
blueprint because its callers authenticate through a server-side secret. Preserve
the runtime's rate limits, body limits, TLS/internal network access and central
logging. Verify real bot create/move/cancel and Website dedup before activation.

No automatic schema creation, owner approval, account setup or deployment is
performed by the factory. Startup health must fail if migration tables are
missing. Until registration, rollback is a code revert. After activation, drain
writers and retain the ledger/receipt data when reverting code; do not switch to
another independent writer or downgrade nonempty tables.
