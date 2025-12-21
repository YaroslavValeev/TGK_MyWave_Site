# Security Policy (MyWave Platform)

## Rules (Non-Negotiable)
- Secrets MUST be provided via ENV only.
- DO NOT commit `.env` files or credential JSON.
- DO NOT paste secrets into logs, screenshots, PRs, issues, or chat.

## Redaction Checklist
Before sharing any logs/screenshots:
- Remove tokens, API keys, credentials JSON, OAuth refresh tokens
- Mask IDs if they are private (Drive folder IDs, Calendar IDs, Spreadsheet IDs)
- Remove PII (phone, email, names)

## Incident Response (Minimal)
If you suspect a leak:
1) Revoke/rotate the compromised secret immediately
2) Remove leaked content from repo history if needed
3) Re-run verification checklist after rotation
