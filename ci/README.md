CI notes
========

This repository uses a two-stage GitHub Actions CI:

- unit-tests: runs pytest against the repo (fast, no external services). Skips UI tests when Playwright isn't installed.
- integration-tests: optional; runs tests in tests/integration and requires a Google service account JSON in the secret `GOOGLE_SERVICE_ACCOUNT_JSON`.

How integration works
--------------------

The integration job reads the `GOOGLE_SERVICE_ACCOUNT_JSON` secret and writes it to `instance/service_account.json` using `scripts/write_service_account.py`.

Environment variables set in CI:

- MYWAVE_DISABLE_FILE_LOG=1 — disable file rotation logging in CI to avoid Windows/permission issues

Run locally
-----------

To simulate the CI integration job locally:

1. Export service account json into env var (replace path/value as needed):

   $env:GOOGLE_SERVICE_ACCOUNT_JSON = Get-Content -Raw ./instance/service_account.json

2. Run the script:

   python scripts/write_service_account.py --env-var GOOGLE_SERVICE_ACCOUNT_JSON --out-file instance/service_account.json

Notes
-----

- Integration tests are gated to reduce accidental runs. The workflow triggers integration on push or when the commit message contains "[run integration]".
- Playwright and other optional dev dependencies are not enforced in unit-tests to keep them fast.
