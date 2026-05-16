# Checklist: замена placeholder → финальный art

**Статус pipeline:** `deploy OK` · `render OK` · **`content NOT OK`** (placeholder gradient webp)

**Runtime:** `3de56f8c` **FROZEN** — код не меняем.

---

## Что делать

1. Получить от дизайна **55 уникальных** webp (см. манифест).
2. Заменить файлы **по тем же путям и именам** в:
   ```text
   static/images/Project/Cards/checklist/
   ```
3. **Не менять:** `checklist.js`, mapping, имена файлов, backend, runtime.
4. `git add` только `static/images/Project/Cards/checklist/**/*.webp`
5. `git push` → на сервере см. **[SERVER_CHECKLIST_ART_DEPLOY.md](SERVER_CHECKLIST_ART_DEPLOY.md)** (готовые команды с git identity).
6. Браузер: https://mywavewake.ru/projects/checklist-org — **Ctrl+F5**
7. Device QA + screenshots → [MOBILE_QA_MATRIX.md](../qa/MOBILE_QA_MATRIX.md)

---

## Требования к файлам

| Параметр | Рекомендация |
|----------|----------------|
| Формат | **webp** (как сейчас) |
| Ориентация | горизонтальная, ~**640×400** или больше (crop через `object-fit: cover`) |
| Размер файла | ориентир **≥ 40 KB** (placeholder сейчас ~3–5 KB) |
| Имена | **строго** как в манифесте (регистр, `_`, папки) |

Полный список путей: [CHECKLIST_ART_FILE_MANIFEST.txt](CHECKLIST_ART_FILE_MANIFEST.txt)

Генерация манифеста:
```bash
python scripts/export_checklist_art_manifest.py
```

---

## Проверка после замены

```bash
python scripts/verify_checklist_assets.py
# missing files 0; placeholder-sized webp (<8KB) должно стать 0
```

```bash
curl -sS -o /dev/null -w '%{http_code} %{size_download}\n' \
  'https://mywavewake.ru/static/images/Project/Cards/checklist/aquatory/aquatory_types_comparison.webp'
```

Ожидаемо: `200` и размер **значительно больше** 8 KB.

---

## Альтернатива (не канон для 55 файлов)

По id чекбокса: `static/images/Project/CheckList_Competion/cards/{id}.webp` — переопределяет путь из JS (нужен deploy с `checklist_art_overrides`). Для массовой поставки art-pack проще **in-place** в `Cards/checklist/`.

---

## Классификация

| Слой | Статус |
|------|--------|
| Deploy / cache | OK |
| JS / CSS / mapping | OK |
| **Content (webp)** | **BLOCKED** — ждём дизайн |
