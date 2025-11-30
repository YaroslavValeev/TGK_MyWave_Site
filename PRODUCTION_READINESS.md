# Production Readiness Checklist

Этот документ описывает 4 компонента, реализованные для подготовки MyWave к production:

## 1. Analytics Endpoint Testing ✅

### Что сделано:

- **Файл:** `scripts/test_analytics_log.py` (314 строк)
- **Назначение:** Тестирует POST `/analytics/log` endpoint с реальными Google Sheets credentials
- **События для тестирования:**
  - `reco_show` — показ блока рекомендаций
  - `reco_click` — клик по рекомендации
  - `booking_view` — просмотр страницы бронирования
  - `calculator_result` — результат калькулятора

### Как использовать:

```bash
# 1. Убедитесь, что приложение запущено
python main.py

# 2. В другом терминале запустите тест (с правильными Google Sheets credentials)
python scripts/test_analytics_log.py

# 3. Проверьте:
#    - Выведен ли результат "✅ 4 events logged successfully"
#    - Появились ли записи в Google Sheet (analytics_statistics)
```

### Endpoint структура:

```text
POST /analytics/log
Content-Type: application/json

{
  "event": "reco_show|reco_click|booking_view|calculator_result",
  "context": "index|services|projects|blog_post|book_success",
  "user_key": "sessionId или phone",
  "rule_id": "services_group|recent_posts|upcoming_events",
  "item_id": "1|2|3 (опционально)",
  "type": "service|post|event (опционально)",
  "meta": { "extra": "data" }  # Опционально
}

Response:
{
  "ok": true
}
```

---

## 2. Service Images Seeding ✅

### Что сделано:​

- **Файл:** `scripts/seed_service_images.py` (160+ строк)
- **Назначение:** Добавляет 10 тестовых записей в таблицу `Image` с `group='services'`
- **Данные:** Реальные названия услуг (Тренировка, Wake Discovery, Wake Camp, etc.)

### Как использовать:​

```bash
python scripts/seed_service_images.py
```

### Вывод:

```text
📸 Добавление 10 изображений услуг...

   ✓ Тренировка на тренажёрах (order=1)
   ✓ Индивидуальные занятия (order=2)
   ...
✅ Успешно добавлено 10 изображений!
📊 Всего в group='services': 10 записей
```

### Результат:

- Рекомендации теперь будут возвращать эти изображения
- Порядок сортировки через `order` поле
- Каждое изображение имеет `title`, `alt`, `caption` для SEO

---

## 3. CSP Browser Monitoring ✅

### Что сделано:​

- **Мониторинг CSP нарушений:** `static/js/csp-monitor.js` (180 строк)
- **API endpoint:** `POST /api/csp-violations` (app/routes/csp_api.py)
- **Интеграция:** Скрипт подключен в `templates/base.html`

### Как работает:

1. **CSP Monitor** (JavaScript) слушает события `securitypolicyviolation`
2. Накапливает нарушения в буфер (максимум 5 за раз)
3. Отправляет на сервер каждые 30 секунд или при переполнении буфера
4. **API endpoint** логирует нарушения в Google Sheets (`csp_violations` лист)

### Что мониторится:

```javascript
{
  violatedDirective: "style-src",      // Какая директива CSP нарушена
  blockedURI: "inline://example.com",  // Какой ресурс заблокирован
  sourceFile: "/services.html",        // Откуда исходит попытка
  lineNumber: 42,
  columnNumber: 15,
  disposition: "enforce|report-only",
  originalPolicy: "..."                // Полная CSP политика
}
```

### Проверка:

```bash
# 1. Откройте DevTools → Console
# 2. Должны видеть:
#    "[CSP Monitor] Инициализирован (sessionId: ...)"

# 3. Если есть нарушения, увидите:
#    "[CSP Violation] { violatedDirective: ... }"

# 4. Проверьте Google Sheet лист "csp_violations"
#    (должны быть пустые строки для production-ready приложения)
```

### Отключение мониторинга (если нужно):

```javascript
window.CSPMonitor.config.enabled = false;
```

---

## 4. Cache Hit/Miss Metrics ✅

### Что сделано:​

- **Метрики в коде:** Добавлены глобальные счётчики в `recommendations_service.py`
- **API endpoint:** `GET /api/reco/stats` (возвращает JSON статистика)
- **Reset endpoint:** `POST /api/reco/stats/reset` (требует X-Admin-Token header)

### Как получить метрики:

```bash
curl http://localhost:5000/api/reco/stats

# Ответ:
{
  "hits": 1234,           # Количество попаданий в кэш
  "misses": 567,          # Количество промахов кэша
  "hit_rate": 68.5,       # Процент попаданий (0-100)
  "cache_size": 12,       # Текущих записей в кэше
  "ttl_seconds": 300,     # Время жизни кэша (сек)
  "total_requests": 1801  # Всего запросов рекомендаций
}
```

### Интерпретация метрик:

- **hit_rate > 60%** ✅ — Хороший кэш, экономим ресурсы БД
- **hit_rate 20-60%** ⚠️ — Среднее, может быть при разных контекстах
- **hit_rate < 20%** ❌ — Плохо, кэш неэффективен, проверьте TTL

### Сброс счётчиков (для тестирования):

```bash
curl -X POST http://localhost:5000/api/reco/stats/reset \
  -H "X-Admin-Token: your_admin_token"

# Ответ:
{ "ok": true, "message": "Cache stats reset" }
```

### Мониторинг в production:

```bash
# Частый мониторинг (через пару часов нагрузки)
watch -n 300 'curl -s http://localhost:5000/api/reco/stats | jq'
```

---

## Complete Verification Checklist

### Скрипт для проверки всего:

```bash
python scripts/verify_production_readiness.py
```

Этот скрипт проверяет:
1. ✅ Database connectivity
2. ✅ API endpoints accessibility
3. ✅ Google Sheets configuration
4. ✅ CSP headers наличие и правильность
5. ✅ Feature flags включены
6. ✅ Service images в базе

### Вывод:​

```text
🚀 Проверка готовности приложения к production

============================================================
  1. Database & Models Check
============================================================
✅ Database connection OK
✅ Found 10 service images

============================================================
  2. API Endpoints Check
============================================================
✅ GET   /api/reco?context=index                → 200
✅ GET   /api/reco/stats                        → 200
✅ POST  /api/csp-violations                    → 400 (ok, empty body)
✅ GET   /analytics/log                         → 405 (GET not allowed)

...
```

---

## Deployment Checklist

Перед запуском в production:

- [ ] Запустить `python scripts/seed_service_images.py` (один раз)
- [ ] Запустить `python scripts/test_analytics_log.py` (проверить Google Sheets подключение)
- [ ] Запустить `python scripts/verify_production_readiness.py` (убедиться, всё зелёно)
- [ ] Проверить в браузере консоль на CSP violations (должны быть нулевыми)
- [ ] Скопировать `ADMIN_TOKEN` в `.env` для управления кэшем
- [ ] Настроить логирование CSP нарушений в мониторинговую систему

---

## Файлы, созданные/изменённые

### Новые файлы:

- `scripts/test_analytics_log.py` — Тест аналитики
- `scripts/seed_service_images.py` — Заполнение БД изображений
- `scripts/verify_production_readiness.py` — Проверка готовности
- `static/js/csp-monitor.js` — Мониторинг CSP в браузере
- `app/routes/csp_api.py` — API endpoint для CSP violations

### Изменённые файлы:

- `app/services/recommendations_service.py` — +метрики кэша (+get_cache_stats, reset_cache_stats)
- `app/routes/recommendations_api.py` — +GET /api/reco/stats, +POST /api/reco/stats/reset
- `templates/base.html` — +CSP monitor скрипт
- `app/__init__.py` — +регистрация csp_bp blueprint

---

## FAQ

### Q: Что если Google Sheets недоступен?

A: Analytix логируются в файл логов (`error`), не прерывая работу приложения. Проверьте `logs/` директорию.

### Q: Как отключить CSP мониторинг для production?

A: Закомментируйте строку в `base.html`:

```html
<!-- <script src="{{ url_for('static', filename='js/csp-monitor.js') }}" nonce="{{ g.csp_nonce }}"></script> -->
```

### Q: Кэш расходуется на что-то ещё?

A: Только на рекомендации. Кэш in-memory, сбросится при перезагрузке приложения.

### Q: Как увеличить TTL кэша?

A: Установите переменную окружения:

```bash
export RECO_CACHE_TTL=600  # 600 секунд (10 минут) вместо 300 (5 минут)
```

---

## Support & Debugging

### Логи:

- Flask логи: STDOUT
- Analytics: Google Sheets + файл логов
- CSP violations: Google Sheets (`csp_violations` лист)
- Errors: `logs/` директория

### Утилиты для отладки:

```bash
# Проверить размер Image таблицы
python -c "from app import create_app; from app.database.models import db, Image; app = create_app(); \
with app.app_context(): print(f'Total images: {Image.query.count()}'); \
print(f'Service images: {Image.query.filter_by(group=\"services\").count()}')"

# Мониторить рекомендации в реальном времени
watch -n 2 'curl -s http://localhost:5000/api/reco?context=index | python -m json.tool'
```

---

**Дата создания:** 2024
**Версия:** 1.0
**Статус:** Production Ready ✅
