# Google Sheets ID — canonical mapping (prod)

**Owner confirmed 2026-06-18** · GM accepted in PR #48 review

| Role | Sheet name | Tail (last 8) | `.env` variable |
|------|------------|---------------|-----------------|
| **Parser News** | MyWave_Parser_News | `LijNNyn50` | `PARSER_NEWS_SPREADSHEET_ID` |
| **Admin / Tg Bot** | MyWave_Admin_Tg_Bot | `akVMOrCgic0` | `SPREADSHEET_ID` |

Full spreadsheet IDs live **only** in server `.env` (not in git). Verify tails after deploy.

**Blog SoT (`raw_feed`):** Parser table only — `.cursor/rules/site-publisher-context.mdc`.

---

## What uses which ID

| Feature | Variable | Expected tail |
|---------|----------|---------------|
| Booking, Schedule, Client_Workouts | `SPREADSHEET_ID` | `akVMOrCgic0` |
| Blog `raw_feed`, publish pipeline | `PARSER_NEWS_SPREADSHEET_ID` | `LijNNyn50` |
| Competitions ticker | `PARSER_NEWS_SPREADSHEET_ID` + `COMPETITIONS_SHEET_NAME` | `LijNNyn50` |
| Social Mission applications | `SOCIAL_SPREADSHEET_ID` or fallback `SPREADSHEET_ID` | `akVMOrCgic0` — tab `Social_Applications` |

Social **must not** point at Parser News unless `Social_Applications` exists there (default: Admin).

---

## Recommended production `.env` (one line per key)

```env
# Admin — booking, clients, Social_Applications (tail akVMOrCgic0)
SPREADSHEET_ID=<full_id_tail_akVMOrCgic0>

# Parser News — blog raw_feed, competitions ticker (tail LijNNyn50)
PARSER_NEWS_SPREADSHEET_ID=<full_id_tail_LijNNyn50>
PARSER_SHEET_NAME=raw_feed

# Social — same Admin table (explicit; optional if SPREADSHEET_ID is Admin)
SOCIAL_SPREADSHEET_ID=<full_id_tail_akVMOrCgic0>
SOCIAL_APPLICATIONS_SHEET_NAME=Social_Applications
```

**Do not** duplicate `SPREADSHEET_ID=` — dotenv **last line wins**; a stray Parser tail on `SPREADSHEET_ID` breaks booking.

---

## Verify on server (tails only — safe for chat)

```bash
cd /var/www/mywave
grep -n '^SPREADSHEET_ID=\|^PARSER_NEWS_SPREADSHEET_ID=\|^SOCIAL_SPREADSHEET_ID=' .env \
  | sed 's/=\(.\{8\}\).*/=***\1/'
```

Expected:

```text
SPREADSHEET_ID=***OrCgic0        (exactly one line)
PARSER_NEWS_SPREADSHEET_ID=***NNyn50
SOCIAL_SPREADSHEET_ID=***OrCgic0  (optional; if empty → fallback SPREADSHEET_ID)
```

Blog diagnostics:

```bash
curl -sS https://mywavewake.ru/api/blog/diagnostics | python3 -m json.tool
# spreadsheet_id_tail → NNyn50
```

Read-only Social readiness: `docs/integration/PROD_SOCIAL_READINESS_ONESHOT.md`

---

## Related

- `docs/deployment/BLOG_CONTENT_VISIBILITY.md`
- `tests/unit/test_parser_news_sheet.py` — tail constants in tests (private repo)
- `env.example` — variable names + tail comments

---

## Staging guard

`automation/staging/_staging_env.py` blocklists prod Admin tail on staging `SPREADSHEET_ID`.
