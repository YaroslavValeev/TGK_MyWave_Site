# Booking storage schema migration

Depends on the storage foundation PR #119 and schema validation PR #118.
Revision `e6f7a8b9c0d1` follows Site's existing head `d8f1a2b3c4e5`.
It adds only `club_box_booking`, `club_box_booking_request` and their constraints
and occupancy index. It does not enable an internal provider or register APIs.

The Core store metadata is included in Site's Alembic target metadata so future
autogenerate runs do not propose dropping these tables merely because they are
not declarative Flask-SQLAlchemy models. No table is created by that metadata step.

## Validation scope

The isolated tests execute the actual Site `migrations/env.py` using a minimal
Flask migration context and a temporary database. They stamp the preceding head
and exercise this additive revision; they do not prove the full historical
migration chain or production runtime readiness. A legacy sentinel table/row
is preserved. The resulting schema is compared against the actual store metadata.
Normal Site CI additionally exercises its fresh-database migration workflow.

From the Site checkout root, without loading a production `.env`:

```text
python -m pytest tests/isolated/test_internal_booking_migration.py --confcutdir=tests/isolated -q -p no:cacheprovider
```

SQLite tests use a temporary file. PostgreSQL tests require an isolated
`TEST_INTERNAL_BOOKING_DATABASE_URL` whose database is `club_box_store_test`.
Never use a live database: the test fixture creates and drops its test tables.

## Before any production activation

1. Merge dependencies and this revision under the Owner Gate; build a pinned
   candidate image with explicit source identity.
2. Confirm the database's actual Alembic head and all application versions which
   can write bookings. Verify a restorable backup and plan a maintenance window.
3. Apply the additive migration using the deployment's verified Flask/Alembic
   runner. Capture its exit status and resulting head. Verify existing services.
4. Keep the internal provider disabled until the separate API/UI integration and
   acceptance checks pass. No fallback to an independent writer is permitted
   once internal booking is enabled.

No production deployment is performed by this PR or these tests. Do not deploy
only this migration file into an old release: its env requires the store module.

## Rollback

For application rollback, preserve the additive tables; older code can run
without using them. Preserve booking and request receipt data in backups.

Downgrade to the preceding head is permitted only when both new tables are
empty. It acquires an exclusive table lock on PostgreSQL or a SQLite writer
lock before checking emptiness, then drops the receipt table before bookings.
All retained rows, including cancelled bookings, block downgrade before DDL.
The guard does not delete or export data. Stop writers before schema maintenance.
Offline downgrade is refused because it cannot check retained data; offline
upgrade SQL is supported. Any data archival/deletion requires a separate owner
decision and verified export/restore procedure.
