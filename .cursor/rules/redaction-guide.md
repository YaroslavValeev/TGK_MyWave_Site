# Redaction Guide (Logs / Screenshots)

## NEVER share
- OPENAI_API_KEY
- Telegram bot tokens
- Google credentials JSON contents
- OAuth refresh tokens
- Private customer data (phone/email/full name)

## Allowed to share (recommended)
- Short request_id/trace_id
- HTTP status code
- Error type (exception class)
- Redacted identifiers (hash or last-4 characters)

## Example
BAD:
- "Authorization: Bearer <token>"
- "service_account.json: { ...private_key... }"

GOOD:
- "GoogleCalendarError: 403"
- "calendar_id: ***redacted***"
- "elapsed_ms: 412"
