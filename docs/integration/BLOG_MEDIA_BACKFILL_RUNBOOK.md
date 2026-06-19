# Blog media backfill / reupload runbook

**Status:** docs-only — **no execution** until separate GM approval  
**Date:** 2026-06-16  
**Owner audit artifact:** `/tmp/blog-media-backfill-candidates-20260616.json` (staging server)

---

## 1. Audit summary (Owner, 2026-06-16)

| Metric | Value |
|--------|-------|
| `total_media_rows` | 30 |
| `placeholders` (Place1Logo) | 10 |
| `review_media_total` | 13 |
| `review_media_http_200_staging` | 0 |
| `review_media_http_200_prod` | 0 |
| `review_media_missing_both` | 13 |
| `external_images` (CDN OK) | 7 |

**Code status (PR #28):** localhost rewrite **PASS** on staging — rendered `/blog` has relative `/static/uploads/review_media/...`, no `127.0.0.1`.

**Availability status:** **OPEN** — files absent on disk (404).

---

## 2. Candidate rows source

Use the Owner audit file:

```text
/tmp/blog-media-backfill-candidates-20260616.json
```

Expected fields per entry (verify against actual JSON):

```text
row_number, id, slug, cover_image_url, image_url, raw_media, media_json, class_hint
```

Export to Sheet snapshot **before** any writeback.

---

## 3. Classification A / B / C / D (10 Place1Logo rows)

| Class | Meaning | Action |
|-------|---------|--------|
| **A** | Genuinely no media in Sheet (`t.me` only, empty `media_json`) | Keep Place1Logo **or** manual cover by Owner |
| **B** | Broken Sheet URL (localhost, `downloads/`, non-image) | Parser reupload + writeback |
| **C** | Valid `/static/uploads/review_media/...` but HTTP 404 | Reupload **or** copy file to disk if source exists elsewhere |
| **D** | External CDN image URL | **No action** |

**Procedure:**

1. Load candidates JSON + cross-check `GET /api/blog/posts?limit=50`.
2. For each Place1Logo slug, assign class A–D in a tracking table.
3. GM approves list of rows to mutate (no mass edit by default).

---

## 4. Reupload plan — 13 missing `review_media` rows

### Canonical storage

```text
<static_folder>/uploads/review_media/review_YYYYMMDD_HHMMSS_<hex>.<ext>
```

- Prod path: `/var/www/mywave/static/uploads/review_media/`
- Staging path: `/var/www/mywave-staging/static/uploads/review_media/`
- **Not in Git** — per-environment filesystem.

### Parser reupload (preferred)

```bash
curl -X POST "$SITE_BASE_URL/api/blog/media/upload" \
  -H "Authorization: Bearer $MEDIA_UPLOAD_TOKEN" \
  -F "file=@/path/to/image.jpg"
```

- Response **201** → `public_url` (relative `/static/...` or `https://<SITE_BASE_URL>/static/...`)
- Write to Sheet: `cover_image_url`, mirror `image_url`, update `raw_media` / `media_json` if used

### Per-row writeback (Parser News owner)

| Field | Rule |
|-------|------|
| `cover_image_url` | **Primary** — new `public_url` |
| `image_url` | Same as cover |
| `raw_media` | Optional JSON `[{"type":"image","url":"..."}]` |
| `media_json` | Optional gallery embed |

**Do not** use Events columns (`media_status`, `media_error`, `source_media_url`).

---

## 5. Sheet snapshot / export (mandatory before edit)

1. Google Sheets → Version history → label `pre-blog-media-backfill-YYYYMMDD`.
2. CSV export of `raw_feed` columns:  
   `row_number`, `id`, `slug`, `cover_image_url`, `image_url`, `raw_media`, `media_json`
3. Change log table:

```text
row_number | slug | old_cover | new_cover | class | actor | timestamp
```

---

## 6. Cache invalidate (after Sheet writeback)

```bash
curl -X POST "$STAGING_BASE_URL/api/blog/cache/invalidate" \
  -H "Authorization: Bearer $MEDIA_UPLOAD_TOKEN"
```

Or wait TTL ~120s (`BLOG_SHEETS_CACHE_TTL`).

---

## 7. Staging smoke checklist

```bash
export STAGING_BASE_URL=http://127.0.0.1:5002

curl -sS "$STAGING_BASE_URL/blog" | grep -oE 'src="[^"]+"' | grep -E '127\.0\.0\.1|localhost|Place1Logo|review_media'

curl -fsSI "$STAGING_BASE_URL/static/uploads/review_media/<filename>.jpg" | head -3

curl -sS "$STAGING_BASE_URL/api/blog/posts?limit=20" | jq '.items[] | {slug, cover_image_url, image_url}'
```

**PASS criteria:**

- No localhost in rendered `src`
- Reuploaded files → HTTP **200**
- Place1Logo count ↓ only where media was restored
- External CDN rows unchanged

---

## 8. Rollback plan

1. Restore Sheet columns from snapshot (version history or CSV re-import).
2. **Do not delete** old upload files on disk (new uploads use new filenames).
3. Code rollback **not required** (PR #28 rewrite is backward-compatible).

---

## 9. Production rollout gate

Production backfill **blocked** until:

- [ ] Staging smoke **PASS**
- [ ] GM written approval for Sheet edit scope
- [ ] Parser confirms source files for all 13 `review_media` rows
- [ ] Separate GM approval for prod deploy / file copy

**Not in scope without approval:**

- `merge to main`
- production deploy
- `mywave-site` restart
- mass parser cron changes

---

## 10. Ownership

| Task | Owner |
|------|--------|
| Audit classification A–D | Parser News + Owner |
| Reupload + Sheet writeback | Parser News |
| Staging/prod file copy (if needed) | Site ops (GM approval) |
| Cache invalidate + smoke | Owner |
| GM gate | GM |

---

## 11. Execution status

```text
EXECUTION: NOT STARTED
AWAITING: GM approval on Phase 1 (reupload 13 rows) + Phase 2 (Place1Logo audit)
```
