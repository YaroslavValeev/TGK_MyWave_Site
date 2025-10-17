fix: calendar guard, safe log rotation, CSRF cookie endpoint (no secrets)

Summary:
- Guard calendar event creation when `GOOGLE_CALENDAR_ID` is missing so booking still succeeds in degraded mode.
- Add `SafeTimedRotatingFileHandler` to avoid windows rollover errors.
- Return CSRF token and set `XSRF-TOKEN` cookie from `/api/csrf-token` endpoint to allow frontend to use `X-CSRFToken` header.
- Remove `configs/service_account.json` from this branch and add runtime logs to `.gitignore` so secrets and logs are not pushed.

Testing:
- Local smoke tests: server starts, GET /api/health returns 200, GET /api/csrf-token sets cookie, POST /api/calendar/book with session+X-CSRFToken returns 201.

Notes:
- This branch intentionally omits `configs/service_account.json`. If you need to test Google integrations, add a service account locally and set `SPREADSHEET_ID`/`GOOGLE_CALENDAR_ID` in your environment or `config`.
- If `configs/service_account.json` was ever committed to other branches, rotate credentials and remove secrets from git history.

Next steps:
1. Create PR from `ci/add-tests-fixes-no-secrets` into `main` (GH CLI or web). Recommended title above.
2. Run CI and review failing tests (if any). I can help fix tests or add mocks for Google APIs.
3. After frontend CSRF integration is verified, remove `@csrf.exempt` where applicable and add tests for booking endpoint.
