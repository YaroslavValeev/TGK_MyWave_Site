# Cursor Prompts Library (MyWave Site + Parser Bot)

All prompts enforce: **Plan → Patches → Verification → Risks/edge cases**  
All prompts assume: minimal safe patch, strict timezone/date rules, idempotency for Calendar + Parser, secrets via ENV only.

---

## 1) Feature (minimal PR)

Implement: {{описание_задачи}}

Success criteria:
{{критерии_успеха}}

Constraints:
- smallest possible patch; minimal files
- DO NOT refactor unrelated code
- routes/controllers HTTP-only; business logic in services; externals via adapters
- timezone-safe; YYYY-MM-DD + HH:MM; published_at ISO 8601
- Calendar + delivery retries must be idempotent; dedup by raw_id/checksum
- secrets via ENV only; respect .cursorignore

Context attached:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 2) Bugfix (reproduce-first)

Fix bug: {{описание_задачи}}

REQUIRED:
1) Provide exact reproduction steps from current code
2) Point to the failing file/function based on attached logs
3) Explain root cause in 3–6 lines
4) Apply the smallest patch possible

Constraints: (same as above)

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 3) Regression-safe Refactor (behavior-preserving)

Refactor scope (STRICT): {{описание_задачи}}

Rules:
- MUST preserve behavior unless explicitly stated
- minimal localized changes only
- no renaming public endpoints/APIs unless requested
- add minimal tests OR manual verification checklist

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}
{{ограничения_и_риски_проекта}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 4) Add Tests / Manual Checklist

Add coverage for: {{описание_задачи}}

Required:
- Detect existing test tooling in the repo (do not introduce new frameworks without request)
- Add minimal tests that catch the regression
- If tests are hard, provide a manual checklist with expected outcomes (step-by-step)

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 5) Google Sheets/Calendar/Drive Change

Change Google integration: {{описание_задачи}}

Non-negotiables:
- timeouts + safe retries + error handling
- safe logging (no secrets, no full PII)
- Calendar idempotency (no duplicates on retries)
- timezone/date formats enforced

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 6) Booking Flow Change (frontend + API contract safety)

Booking change: {{описание_задачи}}

Rules:
- minimal JS/HTML/CSS diff
- preserve date/time formats: YYYY-MM-DD + HH:MM
- confirm API contract from attached code before edits
- handle fetch errors gracefully
- do not break booking → confirmation → persistence → calendar sync

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 7) Chat/WebSocket Stability Change

Stabilize chat/sockets: {{описание_задачи}}

Rules:
- reproduce-first using console + server logs
- prevent double initialization; handlers must not register twice
- reconnect must not spam
- CSP-safe (avoid inline scripts/handlers if CSP is strict)

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 8) Parser Bot Pipeline Change (DTO + dedup + idempotency)

Parser pipeline change: {{описание_задачи}}

Non-negotiables:
- DTO fields: source, raw_id, checksum, published_at (ISO 8601)
- dedup before publish (raw_id/checksum)
- idempotent delivery on retries (no re-publish duplicates)
- safe external calls: timeouts + error handling + safe logs

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}
{{ограничения_и_риски_проекта}}

Output: Plan → Patches → Verification → Risks/edge cases

---

## 9) Security Review / Secrets Audit

Security review focus: {{описание_задачи}}

Required:
- confirm secrets only via ENV; .cursorignore/.gitignore protect credentials
- verify logs do not leak tokens/credentials/PII
- external calls: timeouts + safe error handling
- input validation at boundaries; no excessive debug output

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output: Plan → Findings → Minimal Patches (only if requested) → Verification → Risks/edge cases

---

## 10) Code Review / PR Summary

Review the attached diff/PR.

Rules:
- focus on correctness, regressions, security, idempotency, timezone/date rules
- point out risky changes and missing verification
- propose smallest fixes; no broad refactors

Context:
{{файлы_и_контекст_которые_я_прикрепляю}}

Output:
Plan → Review Notes (by file) → Required Fixes → Verification Steps → Risks/edge cases

---

## “Course Correction” (use when Cursor drifts)

Stop. Revert any unrelated changes. Reduce to the smallest possible patch that satisfies the success criteria. Output Plan → Patches → Verification → Risks/edge cases.