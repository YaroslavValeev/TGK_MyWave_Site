#!/usr/bin/env python3
"""
Тест эндпоинта POST /analytics/log с действительными учётными данными Google Sheets.
Отправляет тестовые события аналитики и проверяет запись в таблицу.

Использование:
    python scripts/test_analytics_log.py

Требует:
    - Запущенное приложение на http://localhost:5000
    - Действительный ANALYTICS_SHEET_SPREADSHEET_ID в окружении или config.py
    - Доступ к Google Sheets API (service_account.json)
"""
import requests
import json
import sys
from datetime import datetime
from pathlib import Path

# Константы
APP_URL = "http://localhost:5000"
ANALYTICS_ENDPOINT = f"{APP_URL}/analytics/log"

# Тестовые события
TEST_EVENTS = [
    {
        "event": "reco_show",
        "context": "index",
        "user_key": "test_user_001",
        "rule_id": "services_group",
        "item_id": "image:1",
        "type": "service",
        "meta": {"count": 4, "position": 0},
    },
    {
        "event": "reco_click",
        "context": "index",
        "user_key": "test_user_001",
        "item_id": "image:1",
        "type": "service",
        "meta": {"duration_ms": 1234},
    },
    {
        "event": "booking_view",
        "context": "services",
        "user_key": "test_user_002",
        "meta": {"service_type": "boat"},
    },
    {
        "event": "calculator_result",
        "context": "wake_discovery",
        "user_key": "test_user_003",
        "meta": {"city": "Moscow", "duration_days": 5, "total_cost": 50000},
    },
]


def test_analytics_log():
    """Тестирует POST /analytics/log с набором событий."""
    print(f"🧪 Тестирование эндпоинта POST {ANALYTICS_ENDPOINT}")
    print(f"⏰ Время теста: {datetime.utcnow().isoformat()}\n")

    success_count = 0
    fail_count = 0

    for idx, event in enumerate(TEST_EVENTS, 1):
        try:
            print(f"📤 Событие {idx}/{len(TEST_EVENTS)}: {event['event']}")
            print(f"   Context: {event.get('context', 'N/A')}")
            print(f"   User: {event.get('user_key', 'N/A')}")

            response = requests.post(
                ANALYTICS_ENDPOINT,
                json=event,
                timeout=5,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                result = response.json()
                if result.get("ok"):
                    print(f"   ✅ Отправлено успешно (200 OK)\n")
                    success_count += 1
                else:
                    print(f"   ⚠️  Ответ без ошибки, но ok=False\n")
                    fail_count += 1
            else:
                print(f"   ❌ Ошибка HTTP {response.status_code}")
                print(f"   Ответ: {response.text}\n")
                fail_count += 1

        except requests.exceptions.ConnectionError:
            print(f"   ❌ Не удалось подключиться к {APP_URL}")
            print(f"   Убедитесь, что приложение запущено на http://localhost:5000\n")
            fail_count += 1
            break
        except Exception as e:
            print(f"   ❌ Ошибка: {str(e)}\n")
            fail_count += 1

    # Итоговый отчёт
    print("\n" + "=" * 60)
    print(f"📊 ИТОГИ ТЕСТА:")
    print(f"   ✅ Успешно: {success_count}/{len(TEST_EVENTS)}")
    print(f"   ❌ Ошибок: {fail_count}/{len(TEST_EVENTS)}")
    print("=" * 60)

    if fail_count == 0:
        print("\n✨ Все события аналитики успешно отправлены!")
        print("📝 Проверьте Google Sheet (ANALYTICS_SHEET_SPREADSHEET_ID)")
        print("   на предмет новых строк в таблице analytics_statistics")
        return 0
    else:
        print(f"\n⚠️  Обнаружены ошибки при отправке событий ({fail_count})")
        return 1


if __name__ == "__main__":
    sys.exit(test_analytics_log())
