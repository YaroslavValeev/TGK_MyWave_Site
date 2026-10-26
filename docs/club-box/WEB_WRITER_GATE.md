# Website writer gate

The internal gateway in PRs #119–122 uses a transactional occupancy ledger.
The existing Website pipeline still uses Calendar/Sheets or YCLIENTS and has
no internal provider registration. Selecting Club Box must not silently fall
through to that independent writer.

`execute_web_booking` therefore refuses requests when `CLUB_BOX_MODE` is true,
or boat requests select `BOAT_PROVIDER=site_internal`. It raises the existing
`CalendarBookingError` handled by the Website route, before duplicate checks,
client resolution, availability calls or external writes. Existing mode-off
Calendar/YCLIENTS behavior is preserved.

This guard is intentionally a release blocker, not a completed Website adapter.
The HTTP handler may validate/read legacy data before entering the pipeline;
other independent writers (including the separate camp branch) are not covered
by this guard. Do not enable the internal gateway or use this patch as proof
that all Site write paths are disabled.

## Required before activation

1. Register an authenticated gateway only in the approved runtime and apply
   the reviewed additive migration after a verified restorable backup.
2. Route Website availability and create/move/cancel to the same club/boat and
   ledger as Telegram. Preserve the ledger booking ID across both interfaces;
   retain a separate stable request/intent ID for each operation/retry.
3. Remove this guard only together with the actual adapter and tests proving
   that no legacy Calendar/Sheets/YCLIENTS writer is reached. Inventory all
   HTTP, AI, camp, admin and background writers, not just `/api/bookings`.
4. Test the actual Website and Telegram consumers against the same disposable
   PostgreSQL database: same-client retry has one record; distinct clients racing
   for the final slot produce one success and one conflict; move/cancel share
   identity and free occupancy. Duration on the wire is seconds (1800 for 30 min).
5. Keep all activation flags OFF until explicit Owner approval of the release,
   configuration, backup/restore and synthetic acceptance evidence.

## Validation and rollback

Run locally from this worktree in PowerShell, with Google/Telegram disabled:

```powershell
$env:ENABLE_GOOGLE_SERVICES='0'
$env:DISABLE_TELEGRAM='1'
$env:SECRET_KEY=[guid]::NewGuid().ToString()
python -m pytest tests/unit/test_booking_phase1.py -q
```

Use a disposable image/database with no production credentials for Docker QA.
This change adds no schema, network call, flag enablement or Compose change.
Rollback before activation is reverting this commit in a reviewed release.
After any ledger activation, drain writers and retain bookings/receipts; reverting
code must not reopen an independent writer or drop retained data.
