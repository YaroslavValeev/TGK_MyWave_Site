# Events-3 staging QA — mobile screenshots (Owner)

**Purpose:** Close final staging sign-off (`PARTIAL` → `PASS`).  
**QA base URL:** `http://127.0.0.1:5002` on VPS (or SSH tunnel from your PC).

Do **not** commit secrets, PII, or full `.env` in screenshots.

---

## 1. How to capture (choose one)

### A. SSH tunnel + desktop Chrome (recommended)

On your PC:

```bash
ssh -L 5002:127.0.0.1:5002 root@<VPS_HOST>
```

Browser: `http://127.0.0.1:5002/events`

1. F12 → Toggle device toolbar (Ctrl+Shift+M)
2. Device: **iPhone 12 Pro** or custom **375 × 812**
3. Capture each view below (Win: Snipping Tool / Mac: Cmd+Shift+4)

### B. Direct on VPS with headless (optional, no GUI)

If no local browser — use phone on VPN to staging nginx **only when DNS works**; otherwise use tunnel (A).

---

## 2. Required files

Save with **exact names** in this folder:

| Filename | Page | What GM expects |
|----------|------|-----------------|
| `events-list-mobile.png` | `/events` | Card grid, dates, no horizontal scroll |
| `events-filters-mobile.png` | `/events` → tap «Фильтры» | Expanded `<details>`, form visible |
| `events-detail-mobile.png` | `/events/1360` | Title, dates, «Подробнее»/CTA if any |
| `home-ticker-mobile.png` | `/` | Competitions/events ticker links readable |

Optional:

| Filename | When |
|----------|------|
| `events-competition-filter-mobile.png` | `/events?type=competition` |
| `events-empty-mobile.png` | Filter with zero results |

---

## 3. Copy screenshots into repo (from PC)

After capture on PC:

```bash
scp events-*-mobile.png root@<VPS>:/var/www/mywave-staging/docs/integration/evidence/events-3-staging/
# Or commit from dev machine into Site_MyWave repo path above
```

On VPS (if saved under staging tree):

```bash
cd /var/www/mywave-staging
ls -la docs/integration/evidence/events-3-staging/*.png
```

Site team commits PNGs to `develop` or Owner attaches to GM report if git commit deferred.

---

## 4. Notify Site / update evidence

Send:

```text
Mobile screenshots: attached
Paths: docs/integration/evidence/events-3-staging/*.png
HEAD: $(git rev-parse HEAD)
```

Site updates `EVENTS_PR3_STAGING_QA_EVIDENCE.md` §1:

- `Mobile screenshots: attached`
- `QA status: PASS`

---

## 5. Checklist before send

- [ ] Viewport ~375px width
- [ ] No cookies/tokens visible
- [ ] URLs show `/events` or `127.0.0.1:5002` (OK for staging evidence)
- [ ] Four required PNGs present
- [ ] Production not touched
