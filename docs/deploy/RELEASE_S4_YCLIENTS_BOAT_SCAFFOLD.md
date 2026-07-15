# Release S4 — YClients boat scaffold (flags OFF)

**Branch:** `release/booking-yclients-boat-v1`  
**Base:** S3 tip (`release/s3-calendar-ics-ux`)  
**Source:** selective files from `efdcb2da` (YClients only — **no** seasonal gym, **no** hero→widget redirect)

## Included

- `app/config/yclients_config.py`
- `app/routes/integrations/yclients.py` — webhook stub (503 when disabled)
- `app/services/booking/providers/{base,yclients}.py`
- `app/services/booking/yclients_sync.py`
- `scripts/sync_yclients_bookings.py`
- tests: `test_yclients_provider.py`, `test_yclients_webhook.py`
- Blueprint + CSRF exempt wiring in `app/__init__.py`
- `env.example` flags documented, default OFF

## Explicitly NOT included (S5+)

- Seasonal gym schedule policy
- `HERO_BOOKING_EXTERNAL_URL` default to YClients widget
- Live provider cutover in booking pipeline
- Credentials / write path

## Production flags (must stay)

```bash
YCLIENTS_ENABLED=0
# BOAT_PROVIDER=site   # or unset
```

## Verify

```bash
python -m pytest tests/unit/test_yclients_provider.py tests/integration/test_yclients_webhook.py -q
```

Deploy to prod is optional for S4 (code-only scaffold). Prefer deploy **after** S3 Calendar ICS is live, still with `YCLIENTS_ENABLED=0`.
