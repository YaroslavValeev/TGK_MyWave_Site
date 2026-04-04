# Legacy / Deprecated — статус (Sprint 3)

## Удалено без риска

_Пока ничего не удалено агрессивно._

---

## Помечено deprecated / временно оставлено

| Компонент | Статус | Причина |
|-----------|--------|---------|
| `server.js` | **Legacy** | Node/Express прокси для чата. Основное приложение — Flask (`main.py`). Использовать только если нужен отдельный chat-proxy. |
| `/api/chat` | **Deprecated** | Compatibility layer. Основной endpoint — `/chat/api`. Оставлен для обратной совместимости. |
| `GET /chat/` | **Актуально** | Лендинг «Чат с экспертом» + тот же плавающий виджет из `base.html` (раньше ссылка вела в 404). |
| `app/modules/admin.py` | **Не используется** | Blueprint `admin_panel` не зарегистрирован. Активная админка — `app/routes/admin/` и `admin_images`. |
| `admin_events`, `admin_blog`, `admin_users`, `admin_settings` | **Ссылки убраны** | Blueprint'ы не существуют. Ссылки в админке заменены на `admin.index` (в разработке). |

---

## Оставлено как совместимость

| Компонент | Причина |
|-----------|---------|
| `/api/chat` | Обратная совместимость; проксирует в `chat_handler` |
| `server.js` | Может использоваться как альтернативный standalone chat proxy |

---

## Рекомендации

- **server.js**: документировать как optional; не удалять без решения команды
- **/api/chat**: оставить; frontend уже на `/chat/api`
- **admin**: разбить на blueprint'ы по мере необходимости (blog, events, users, settings)
