# PR #48 — Social remediation (GM-approved A + B)

**Status:** remediation approved · **rollout NOT approved**  
**Hero blocker:** CLOSED / PASS  
**Social blocker:** OPEN until A+B + readiness PASS

---

## Approval A — `.env` dedupe (prod only)

### Backup (required)

```bash
TS=$(date +%Y%m%d_%H%M%S)
sudo mkdir -p /var/backups/mywave
sudo cp /var/www/mywave/.env "/var/backups/mywave/.env.pre_social_remediation_${TS}"
echo "backup=/var/backups/mywave/.env.pre_social_remediation_${TS}"
```

### What to change

| Line | Action |
|------|--------|
| **L31** `SPREADSHEET_ID=…` (tail `ijNNyn50` / Parser) | **DELETE** |
| **L36** `SPREADSHEET_ID=…` (tail `MOrCgic0` / Admin) | **KEEP** |
| **L133** `PARSER_NEWS_SPREADSHEET_ID=…` | **KEEP** unchanged |
| `SOCIAL_SPREADSHEET_ID` | keep if set to Admin; optional |

```bash
sudo nano /var/www/mywave/.env
# or: sudo sed -i '31d' /var/www/mywave/.env   # ONLY if line 31 is still the Parser duplicate — verify with grep -n first
```

### Verify (no restart required for this check)

```bash
grep -n '^SPREADSHEET_ID=\|^PARSER_NEWS_SPREADSHEET_ID=\|^SOCIAL_SPREADSHEET_ID=' /var/www/mywave/.env \
  | sed -E 's/=.*(.{8})$/=***\1/'
```

Expected:

```text
SPREADSHEET_ID=***MOrCgic0          (exactly one line)
PARSER_NEWS_SPREADSHEET_ID=***ijNNyn50
SOCIAL_SPREADSHEET_ID=***MOrCgic0   (optional)
```

**Guardrails:** no token/SA JSON changes · no restart for verify · no Parser/TGbotAdmin edits.

---

## Approval B — `Social_Applications` tab (Admin sheet only)

**Headers source (canonical):** `app/services/social_schema.py` → `SOCIAL_APPLICATIONS_HEADERS`

### Exact header row (row 1, 23 columns)

```text
application_id	created_at	updated_at	status	parent_name	parent_phone	parent_email	child_first_name	child_age	city	preferred_contact	telegram_username	health_notes	motivation_text	consent_personal_data	consent_training	consent_media	consent_version	source	ip_hash	assigned_admin	booking_id	internal_notes
```

Comma-separated (for scripts):

```text
application_id,created_at,updated_at,status,parent_name,parent_phone,parent_email,child_first_name,child_age,city,preferred_contact,telegram_username,health_notes,motivation_text,consent_personal_data,consent_training,consent_media,consent_version,source,ip_hash,assigned_admin,booking_id,internal_notes
```

**Manual (Sheets UI):** Admin spreadsheet → Add sheet `Social_Applications` → paste header row above → **no data rows**.

### Script (recommended — idempotent)

Dry-run (prints headers, checks tab):

```bash
PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python /tmp/prod_create_social_applications_tab.py
```

Apply (creates tab + row 1 only):

```bash
SOCIAL_TAB_CREATE_APPLY=1 PROD_ROOT=/var/www/mywave \
  /var/www/mywave/venv/bin/python /tmp/prod_create_social_applications_tab.py
```

Copy script to prod before PR #48 merge:

```bash
scp scripts/prod_create_social_applications_tab.py user@prod:/tmp/
```

**Scope:** Admin sheet only · tab `Social_Applications` · header row only · no backfill · no booking/client/raw_feed edits.

---

## After A + B — Social readiness rerun

```bash
PROD_ROOT=/var/www/mywave /var/www/mywave/venv/bin/python /tmp/prod_social_readiness_oneshot.py
```

Expected **PASS:**

```text
SPREADSHEET_ID line count: 1
SPREADSHEET_ID tail: MOrCgic0
PARSER_NEWS tail: OK (ijNNyn50)
effective_social_tail: MOrCgic0
spreadsheet_access=OK
Social_Applications_tab YES
headers_valid=YES (if using create script)
```

---

## GM report template (paste after remediation)

```text
.env backup path:
.env dedupe done: yes/no
SPREADSHEET_ID count:
Admin tail:
Parser tail:
Social effective tail:
Social_Applications tab created: yes/no
Headers source: app/services/social_schema.py SOCIAL_APPLICATIONS_HEADERS
Social readiness rerun: PASS/FAIL
Output:
Production execution: NOT STARTED
```

---

## Still NOT approved

merge PR #48 · prod UI rollout · `mywave-site` restart for rollout · Social flags ON · other Sheet edits · backfill · Parser cron · TGbotAdmin · Events launch
