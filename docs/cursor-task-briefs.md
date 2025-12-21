# Cursor Task Briefs (MyWave Site + Parser Bot)

Use these briefs to attach the *minimum necessary context* and force Cursor to stay inside project rules.
Always keep the brief to 3–7 lines + attachments.

---

## 0) Universal Brief Template (copy/paste)

**Task:** {{описание_задачи}}  
**Expected:** {{критерии_успеха}}  
**Repro (if bug):** 3–6 steps + expected vs actual  
**Scope:** smallest set of files/modules only  
**Constraints:** timezone + formats; idempotency; no secrets; minimal patch  
**Attachments:** {{файлы_и_контекст_которые_я_прикрепляю}}  
**Risks:** {{ограничения_и_риски_проекта}}

Cursor command:
> "Before editing: list the rules you will apply from .cursor/rules, then output Plan only."

---

## 1) Booking (Site MyWave) — Brief

**Task:** {{описание_задачи}}  
**Repro:**  
1) Open Home → click “Book/Записаться”  
2) Select date → slots load  
3) Choose slot → enter contact → confirm  
**Expected vs Actual:** {{критерии_успеха}}  
**Constraints:** YYYY-MM-DD + HH:MM; single timezone; no naive/aware mixing; no unrelated refactors  
**Attachments (@Files):**
- Backend routes: booking/calendar-related routes + blueprint registration
- Services/adapters: sheets/calendar/drive adapters/services
- Frontend: booking.js + relevant templates
- Logs: server traceback + browser console + network request/response (redacted)

Cursor command:
> "Reproduce-first. Do not patch until you pinpoint root cause in the attached files."

---

## 2) Calendar Sync — Idempotency Brief

**Task:** {{описание_задачи}}  
**Repro:** repeat the same booking action twice (simulate retry)  
**Expected:** single Calendar event (update-if-exists), no duplicates  
**Constraints:** idempotent create/update; safe retries; timeouts; no secrets in logs  
**Attachments (@Files):**
- Calendar adapter/service where event identity is formed
- Booking → calendar orchestration code
- Example redacted payload + Google API error

Cursor command:
> "Implement deterministic idempotency. Retries must not create duplicates. Minimal patch."

---

## 3) Chat / Sockets Stability — Brief

**Task:** {{описание_задачи}}  
**Repro:** open chat → send message → refresh → send again  
**Expected:** no crashes, no duplicate handlers, no reconnect spam  
**Constraints:** CSP-safe; avoid double socket initialization; minimal JS diff  
**Attachments (@Files):**
- chat.js + socket init
- websocket handler/init on backend
- CSP headers/config (if present)
- Browser console + server logs

Cursor command:
> "Fix crash first. Do not redesign chat UI. Provide minimal patch + verification."

---

## 4) Parser Bot Pipeline — Dedup & Idempotency Brief

**Task:** {{описание_задачи}}  
**Repro:** run pipeline twice on same input  
**Expected:** no duplicate storage/publish; published_at ISO 8601  
**Constraints:** dedup by raw_id/checksum; idempotent delivery; safe retries; timeouts for external calls  
**Attachments (@Files):**
- collectors/ processors/ publishers/ orchestrator
- DTO/event model defining raw_id/checksum/published_at
- storage layer (Sheets/DB) + dedup stage
- sample raw input + expected normalized output (redacted)

Cursor command:
> "Dedup BEFORE publish. Ensure delivery idempotency. Minimal localized changes only."

---

## 5) Google Sheets/Drive Changes — Brief

**Task:** {{описание_задачи}}  
**Expected:** {{критерии_успеха}}  
**Constraints:** timeouts + error handling; safe logging; no secrets; no duplicate writes on retries  
**Attachments (@Files):**
- google sheets/drive adapter
- service that orchestrates write/upload
- logs/errors (redacted)

Cursor command:
> "Treat Google APIs as external: timeouts, safe retries, minimal patch, no secrets."

---

## 6) “Ask Questions First” Gate (use when context is incomplete)

Paste this when you did not attach enough context:

> "Stop. Before making any edits, list the exact missing context (file paths + logs + repro details). Do not propose a patch until the missing context is provided."
