# Production Audit Log — MyWaveWake

**Production:** https://mywavewake.ru  
**Цель:** operational memory · deploy history · rollback traceability · production intelligence

После каждого production deploy добавляйте строку. Release details — в [releases/](../releases/).

---

## Audit log

| Date | Change | Release Type | Commit | Result | Notes |
|------|--------|--------------|--------|--------|-------|
| 2026-05 | Timeweb production baseline | ops | `68b46537` | PASS | initial prod deploy |
| 2026-05 | Post-deploy pack (health, mobile v1) | mixed→split | `8ee0ca40` | PASS | pre-freeze era |
| 2026-05 | **Runtime freeze** — blog/health P0 | runtime | `3de56f8c` | PASS | **FROZEN baseline** |
| 2026-05 | Frontend mobile v3 + smoke scripts | frontend | `48dc9c64` | PASS | active UX baseline |
| 2026-05 | QA/Ops governance artifacts | ops | `0a2a0e1a` | PASS | matrix, incident policy, gate |
| 2026-05 | Production state governance docs | ops | `94fbc211` | PASS | canonical state |
| 2026-05 | Governance index + release taxonomy | ops | `4d1ded82` | PASS | PRODUCTION_GOVERNANCE index |
| 2026-05 | Formal runtime governance | ops | `30f991da` | PASS | RUNTIME_GOVERNANCE.md |
| 2026-05 | Phase transition canon | ops | `56b98c49` | PASS | formal phase |
| 2026-05 | Platform canon + execution model | ops | `15ee2680` | PASS | stabilization execution |
| 2026-05-15 | **Operational Maturity Phase** — maturity artifacts | ops | `1858292d` | PASS | ownership, env, audit log, releases |
| 2026-05-15 | Operational Maturity Phase charter | ops | `258c4df5` | PASS | phase doc, post-deploy policy |
| 2026-05-15 | Platform state canonical snapshot | ops | `23ab28ee` | PASS | PLATFORM_STATE.md |
| 2026-05-15 | Canonical 5-doc governance stack | ops | `2a8a5256` | PASS | governance model sync |
| 2026-05-15 | Operational governance model canon | ops | `13612e63` | PASS | PLATFORM_STATE + docs README |
| 2026-05-15 | Ownership matrix filled + Mobile QA run pack | ops | `0d07eee7` | INTEGRATED | ownership filled; QA PENDING devices |
| 2026-05-15 | Operational pack refs sync | ops | `544f518a` | PASS | governance stack synced |
| 2026-05-15 | Engineering maturity roadmap canon | ops | `af153b05` | PASS | phased execution integrated |
| 2026-05-15 | Mobile QA automated pre-check | ops | `000a7100` | PARTIAL | smoke PASS; prod mobile-home v=2 not v=3 |
| 2026-05-15 | Phase 1 status board + Step 0 deploy runbook | ops | `b851d634` | PASS | Step 0 closed |
| 2026-05-15 | Precheck gzip fix (`curl --compressed`) | ops | `3ae20741` | PASS | automated precheck aligned with manual curl |
| 2026-05-15 | Phase 1 Step 0 — prod HTML mobile-home v=3 | frontend | restart | PASS | manual curl OK; templates ?v=3 |
| 2026-05-15 | Precheck script — HTML check order + grep -F | ops | `dc08c500` | PASS | fixes false FAIL when manual curl OK |
| 2026-05-15 | Phase 1 → manual device QA blocker | ops | `dc08c500` | OPEN | A1/A2/I1/T1 |
| 2026-05-16 | Checklist card art img + cardbg13 | frontend | `ad71c02b` | PASS | pipeline ready; placeholder webp |
| 2026-05-16 | Reviews student photos restore | frontend | `3d718a00` | PASS | images_old → images/students; ?v=2 |
| 2026-05-17 | GM team status — Phase 1 blocker = device QA only | ops | — | OPEN | [TEAM_STATUS_2026-05-17.md](TEAM_STATUS_2026-05-17.md) |
| 2026-05-17 | Checklist cardbg14 + blog xlsx analysis + server runbook | frontend/ops | `ad9f2b80` | PASS | placeholders OK; blog content = Sheets sync |
| 2026-05-17 | Blog smoke P2 — quoted sheet range + fallbacks | tooling | `1c3795de` | PASS | script only, not runtime |
| 2026-05-17 | Server `git pull` + verify PASS; push from prod rejected (fetch first) — expected | ops | `13ffaf36` | PASS | deploy target policy; no server push |
| 2026-05-17 | Checklist final art pushed to `main` (~49 webp, ~150 MB) | content | `1976d637` | PARTIAL | 53/62 final; 9 participant still placeholder; prod pull pending |
| 2026-05-17 | Remove accidental PNG from checklist folder | content | `c8101ae2` | PASS | cleanup after art commit |
| 2026-06-28 | **PR56 Social manual assign** — Phase A/B, PR66 auth, alignment | runtime | `3b70a038` | PASS | manual assign ENABLED; evidence [pr56](../evidence/pr56/README.md) |
| 2026-06-29 | **PR56 post-release monitoring** D0–D2 closure | ops/docs | `df24a4d9` | PASS | CLOSED/PASS; no prod deploy; [QA log](../evidence/pr56/QA_MONITORING_LOG.md) |
| 2026-07-07 | **PR97** public CTA unify + product card click | frontend | `43dc7ca2` | PASS | Owner QA PASS; rollback `beb5c8ad`; [release](../releases/2026-07-07-frontend-public-cta-product-card-click.md) |

---

## Шаблон новой записи

```markdown
| YYYY-MM-DD | <краткое описание> | runtime/frontend/content/ops | `<shortsha>` | PASS/FAIL/ROLLBACK | smoke: OK; QA: N/A |
```

---

## Связанные артефакты

| Артефакт | Путь |
|----------|------|
| Release notes | [docs/releases/](../releases/) |
| Rollback | [POST_DEPLOY_ROLLBACK.md](../deployment/POST_DEPLOY_ROLLBACK.md) |
| Gate | [RELEASE_GATE_CHECKLIST.md](../deployment/RELEASE_GATE_CHECKLIST.md) |
