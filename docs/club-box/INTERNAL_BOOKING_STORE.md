# Internal booking storage foundation

This layer uses the existing Site SQLAlchemy engine (SQLite or PostgreSQL).
It does not register endpoints, select a provider, create tables automatically,
or change live bookings. It is a foundation for the Club Box internal gateway,
not a completed gateway or portable release.

## Contract

- `InternalBookingStore(engine, club_id)` scopes every operation to one club.
- `create(BookingRequest(...))` persists one boat's occupancy interval.
- Input phone is normalized E.164; start must carry an explicit UTC offset and
  align to a minute. The boundary adapter must reject ambiguous/nonexistent
  local times before conversion. Duration is 1–1440 minutes.
- Same idempotency key and original normalized payload returns the same booking,
  including after move or cancellation. Changed payload with that key conflicts.
- Matching active phone/boat/interval with a different interface key returns the
  same booking and records that key's receipt. No new booking is created.
- Concurrent overlapping writes for different clients yield one success and one
  conflict. Adjacent intervals are allowed. Different boats/clubs are independent.
- `move` keeps the booking id; a conflicting move leaves the old interval intact.
- `cancel` is repeatable, releases occupancy, and cannot be undone by retrying
  creation. A cancelled booking cannot be moved. A new booking needs a fresh key.
- `available` is a read hint, not a reservation; `create` rechecks atomically.

PostgreSQL takes a transaction-scoped advisory lock per club and uses READ
COMMITTED so reads after lock acquisition see the previous writer's commit.
SQLite takes BEGIN IMMEDIATE. Writer isolation is explicitly selected even if
the supplied engine uses AUTOCOMMIT or REPEATABLE READ.

All writers must use this store. Its advisory locks do not protect against
independent code writing the tables directly. No calendar/Sheets/CRM calls or
network notifications occur inside the transaction. PII is stored in the existing
database and is not logged by this layer; ordinary database ACL/backup/retention
policy must apply. Request fingerprints are not anonymized export data.

## Integration prerequisites

1. A separate reviewed Alembic migration must create `club_box_booking` and
   `club_box_booking_request` from the declared metadata. Migration/import must
   not silently activate the provider. Test upgrade/downgrade on disposable DBs.
2. API adapter must enforce owner/auth gates, enabled modules, allowed boat ids,
   club timezone/season/opening hours, allowed durations/prices and request limits.
3. Both Website and Telegram Admin must use that gateway for create/move/cancel
   and availability. Enabling internal mode must prohibit legacy write fallback.
4. Bind storage lifecycle and backups to the Club Box instance. No old club
   database, client records, tokens or request receipts belong in distribution.

## Validation and rollback

Run from the Site checkout root:

```text
python -m pytest tests/isolated/test_internal_booking_store.py --confcutdir=tests/isolated -q -p no:cacheprovider
```

Tests default to temporary SQLite. For a disposable PostgreSQL test instance,
provide `TEST_INTERNAL_BOOKING_DATABASE_URL` with database name
`club_box_store_test`. The fixture creates and drops only these two tables; NEVER
point this variable at a live database. The tests do not load Site's `.env`.

This PR has no production activation or schema migration. Before integration,
rollback is reverting this code. Once schema/storage are deployed, preserve and
back up booking/receipt data; migration rollback and provider switching require
their own reviewed plan. Do not drop live tables to revert Python code.
