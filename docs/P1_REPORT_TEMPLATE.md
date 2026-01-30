# P1: Шаблон отчёта «готово в проде»

Заполнить после выполнения: MERGE+PUSH, DEPLOY, QA smoke.

---

## 1. Хэш(и) в main и PR/мерж

**Коммиты P1.0 (должны быть в main после мержа/пуша):**

- `b1678281` — domain fix (mywavetreaning.ru) + approve-gate  
- `e075912c` — P1.0 writeback review_queue=FALSE + final_version, CONTRACT read-only, docs  
- `6f51f53b` — docs: P1 release checklist и плейсхолдеры QA/deploy в Decision Log  

**Хэш(и) в main после мержа (актуальный main):** _______________  

**Ссылка на PR/мерж (если был):** _______________  

---

## 2. Подтверждение деплоя

**Окружение:** production  

**Дата:** _______________  

**Подтверждение:** В проде canonical_url формируется строго как `https://mywavetreaning.ru/blog/{slug}`. В fallback нет mywavetraining.ru.

---

## 3. Две ссылки на проверочные строки в Sheets и результат по кейсам

**База ссылки на таблицу:**  
https://docs.google.com/spreadsheets/d/1RJpw2mAMej3a-VC6yKAsKkVQvzGStcjUC7LijNNyn50/edit?gid=1039755742

**Кейс A (WAITING_REVIEW):**  
- Ссылка на строку: _______________  
- Результат: _______________ (например: не публикуется, publish_error пусто, attempts не выросли — OK)

**Кейс B (PUBLISHED):**  
- Ссылка на строку: _______________  
- Результат: _______________ (например: опубликовано, review_queue=FALSE, final_version=published:{slug} — OK)

---

После заполнения скопировать в ответ Ярославу или в `docs/DECISION_LOG_R2_P1.md` (секция «Релиз и QA на проде»).
