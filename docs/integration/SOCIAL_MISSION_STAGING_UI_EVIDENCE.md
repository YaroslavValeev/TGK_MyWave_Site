# Social Mission — staging UI evidence (Social-2/4)

## Scope

- `GET /social` — public landing + application form
- `POST /api/social/apply` — Sheets write via `append_social_application`
- Home widget partial (flag-gated)
- **No** auto booking / calendar / slot occupation

## Flags (default OFF)

```text
SOCIAL_MODULE_ENABLED=false
SOCIAL_WIDGET_ENABLED=false
SOCIAL_APPLICATIONS_ENABLED=false
SOCIAL_PUBLIC_STATS_ENABLED=false
SOCIAL_ADMIN_NOTIFICATIONS_ENABLED=false
```

Staging QA: enable flags in staging `.env` **only after GM approval**.

## Files

- `app/routes/social.py`
- `app/services/social_stats.py`
- `templates/social/index.html`
- `templates/partials/social_application_form.html`
- `templates/partials/social_mission_widget.html`
- `static/css/social-mission.css`
- `static/js/social-application-form.js`

## Tests

```bash
python -m pytest tests/unit/test_social_routes.py tests/unit/test_social_store.py tests/unit/test_social_features.py -q
```

## Manual QA (Owner)

- [ ] `/social` 200 with flags ON
- [ ] Form submit → 201, row in Social_Applications (staging Sheet)
- [ ] Home widget visible with `SOCIAL_WIDGET_ENABLED=1`
- [ ] No `/api/booking` or calendar calls on apply (network tab)
- [ ] Desktop + mobile screenshots

## Production

Not deployed. `main` unchanged until GM approval.
