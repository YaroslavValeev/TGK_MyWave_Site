# P1: Чеклист релиза «готово в проде»

**Цель:** Довести P1.0 до готово в проде без техдолга.

---

## 1. MERGE + PUSH в main + DEPLOY (блокер)

**Ответственный:** Release / Deploy

- [ ] Коммиты в main:
  - `b1678281` — domain fix (mywavetreaning.ru) + approve-gate
  - `e075912c` — P1.0 writeback review_queue=FALSE + final_version, CONTRACT read-only, docs
- [ ] При необходимости: мерж ветки в main, разрешение конфликтов, push `origin main`
- [ ] Деплой на прод (по процедуре проекта)
- [ ] **DoD:** В проде canonical_url всегда `https://mywavetreaning.ru/blog/{slug}`. Никаких упоминаний mywavetraining.ru в fallback.

**Команды (если пушим текущий main):**
```bash
git fetch origin
git pull origin main   # если нужно подтянуть удалённый main
git push origin main   # отправить коммиты b1678281, e075912c
```

После деплоя заполнить в `docs/DECISION_LOG_R2_P1.md`: хэш(и) в main, ссылку на PR (если был), окружение и дату деплоя.

---

## 2. QA smoke: approve-gate + writeback (2 кейса)

**Ответственный:** QA / Control-run

**Таблица:** https://docs.google.com/spreadsheets/d/1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50/edit?gid=1039755742

### Кейс A (WAITING_REVIEW)

- Подготовить строку: `status=READY_TO_PUBLISH`, `review_queue=TRUE`, `approved_by` и `approved_at` пустые, контент готов.
- Запустить публикацию (cron или вручную).
- **Ожидание:** запись не публикуется; в таблице `publish_error` пусто, `publish_attempts` не увеличился; в логах есть WAITING_REVIEW.
- Зафиксировать: ссылку на строку в Sheets, краткий результат (OK / fail).

### Кейс B (PUBLISHED)

- Подготовить строку: `status=READY_TO_PUBLISH`, `review_queue=TRUE` или любое, `approved_by` или `approved_at` заполнен, контент готов, `row_number` валиден.
- Запустить публикацию.
- **Ожидание:** пост опубликован; в таблице `review_queue=FALSE`, `final_version=published:{slug}` (если колонка есть), canonical_url заполнен.
- Зафиксировать: ссылку на строку в Sheets, краткий результат (OK / fail).

После прогона заполнить в `docs/DECISION_LOG_R2_P1.md` две ссылки на проверочные строки и результат по каждому кейсу.

---

## 3. Документация (P1 фиксация)

**Ответственный:** Docs

- [ ] В main присутствуют:
  - `docs/DECISION_LOG_R2_P1.md`
  - `docs/P1_STATUS.md`
  - обновлённый `docs/P1_PLAN_AND_STATUS.md`
- [ ] В Decision Log P1 зафиксированы: правило approve-gate, writeback review_queue/final_version, read-only CONTRACT (уже внесено).
- [ ] После QA в Decision Log P1 заполнены: хэши в main, деплой, 2 ссылки на строки, результат по кейсам A и B.

---

## Отчёт для Ярослава (после выполнения)

- Хэш(и) в main и ссылка на PR/мерж (если был).
- Подтверждение деплоя (окружение/дата).
- 2 ссылки на проверочные строки в Sheets и короткий результат по кейсам A и B.

Текст отчёта можно взять из заполненной секции «Релиз и QA на проде» в `docs/DECISION_LOG_R2_P1.md`.
