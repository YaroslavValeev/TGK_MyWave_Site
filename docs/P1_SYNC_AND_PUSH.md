# P1.0: Синхронизация main с origin и push

Локальный main расходится с origin/main (у вас 3 коммита P1.0, на origin — 45 других). Выполнить под своими учётками.

---

## Команды (PowerShell, в корне репозитория)

```powershell
cd "E:\Проекты MyWave\Site_MyWave"

git status
git fetch origin

# Вариант A (предпочтительно): rebase — «приклеить» свои коммиты поверх origin/main
git pull --rebase origin main
```

**Если при rebase появятся конфликты:**

1. Разрешить конфликты в файлах (отредактировать, убрать маркеры `<<<<<<<`, `=======`, `>>>>>>>`).
2. Затем:
   ```powershell
   git add .
   git rebase --continue
   ```
3. При необходимости повторять, пока rebase не завершится.

**После успешного rebase:**

```powershell
# Минимальная проверка (опционально): запуск приложения или тестов
# python main.py
# или: pytest tests/ -q -x --tb=short

git push origin main
```

**Проверка на GitHub:**

- Открыть репозиторий → ветка main → история коммитов.
- Должны присутствовать коммиты P1.0 (возможно с новыми хэшами после rebase):
  - domain fix + approve-gate
  - writeback review_queue=FALSE + final_version, CONTRACT read-only, docs
  - docs: P1 release checklist и плейсхолдеры

---

## Разделение задач (subagents)

| Subagent | Задача |
|----------|--------|
| **Release/Deploy** | Выполнить команды выше (rebase + push), затем деплой main на production по процедуре. Контроль: canonical_url только `https://mywavetreaning.ru/blog/{slug}`. |
| **Infra** | 301-редиректы альтернативных доменов на mywavetreaning.ru; SERVER_NAME / reverse-proxy headers при необходимости. |
| **QA** | 2 smoke-кейса (A: WAITING_REVIEW, B: PUBLISHED) по `docs/P1_RELEASE_CHECKLIST.md`; заполнить в Decision Log P1 ссылки на строки и статусы. |

После push + deploy + QA заполнить секцию «Ответ для Ярослава» в `docs/DECISION_LOG_R2_P1.md` и отправить ответ.
