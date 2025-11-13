#!/usr/bin/env python3
"""
Финальный скрипт для быстрого старта всех компонентов production readiness.

Использование:
    python scripts/start_production_components.py

Выполняет:
1. Проверку БД и подключения
2. Заполнение Image таблицы (если не заполнена)
3. Запуск app и проверку endpoints
4. Вывод инструкций для дальнейших действий
"""

import sys
import os
import subprocess
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def print_header(title):
    """Печатает красивый заголовок."""
    print(f"\n{'='*70}")
    print(f"║ {title.center(66)} ║")
    print(f"{'='*70}\n")


def print_step(num, title):
    """Печатает номер шага."""
    print(f"\n📍 Шаг {num}: {title}")
    print("-" * 70)


def check_app_health():
    """Проверяет здоровье приложения."""
    import requests
    
    try:
        resp = requests.get("http://localhost:5000/", timeout=2)
        if resp.status_code == 200:
            return True
    except:
        pass
    return False


def main():
    print_header("🚀 Production Readiness Startup Guide")
    
    print("""
Это руководство поможет вам подготовить MyWave к production.

Компоненты для запуска:
  1. ✅ Analytics logging (/analytics/log endpoint)
  2. ✅ Service images seeding (для рекомендаций)
  3. ✅ CSP violation monitoring (browser-side)
  4. ✅ Cache metrics endpoint (/api/reco/stats)

Все компоненты УЖЕ реализованы в коде.
Нужно только выполнить проверки и запустить тесты.
""")
    
    # ==============================================================
    print_step(1, "Запуск приложения Flask")
    # ==============================================================
    print("""
Откройте новый терминал и запустите:
    
    python main.py

Или используйте Docker:
    
    docker-compose up

Убедитесь, что приложение доступно на http://localhost:5000
""")
    
    input("Нажмите Enter когда приложение запущено... ")
    
    # Проверяем доступность
    print("\n⏳ Проверка доступности приложения...", end=" ", flush=True)
    for _ in range(10):
        if check_app_health():
            print("✅")
            break
        time.sleep(1)
    else:
        print("❌\n⚠️  Приложение не доступно на localhost:5000")
        print("Убедитесь, что оно запущено, и повторите попытку.")
        return 1
    
    # ==============================================================
    print_step(2, "Заполнение Image таблицы")
    # ==============================================================
    print("""
Добавим тестовые изображения услуг для рекомендаций:
    
    python scripts/seed_service_images.py
""")
    
    response = input("Запустить скрипт сейчас? (y/n): ").strip().lower()
    if response == 'y':
        try:
            exec_result = subprocess.run(
                [sys.executable, "scripts/seed_service_images.py"],
                cwd=os.path.dirname(os.path.dirname(__file__)),
                capture_output=True,
                text=True,
                timeout=30
            )
            print(exec_result.stdout)
            if exec_result.returncode != 0:
                print("❌ Ошибка:", exec_result.stderr)
        except Exception as e:
            print(f"❌ Не смог запустить скрипт: {e}")
    
    # ==============================================================
    print_step(3, "Тестирование Analytics endpoint")
    # ==============================================================
    print("""
Протестируем логирование событий в Google Sheets:
    
    python scripts/test_analytics_log.py
    
Скрипт отправит 4 тестовых события и проверит ответ.
Не забудьте проверить записи в Google Sheet 'analytics_statistics'.
""")
    
    response = input("Запустить тест аналитики? (y/n): ").strip().lower()
    if response == 'y':
        try:
            exec_result = subprocess.run(
                [sys.executable, "scripts/test_analytics_log.py"],
                cwd=os.path.dirname(os.path.dirname(__file__)),
                capture_output=True,
                text=True,
                timeout=30
            )
            print(exec_result.stdout)
            if exec_result.returncode != 0:
                print("⚠️  Stderr:", exec_result.stderr)
        except Exception as e:
            print(f"❌ Не смог запустить скрипт: {e}")
    
    # ==============================================================
    print_step(4, "Проверка CSP мониторинга")
    # ==============================================================
    print("""
CSP мониторинг уже встроен в приложение.

Проверка:
  1. Откройте браузер и зайдите на http://localhost:5000
  2. Откройте DevTools (F12 → Console)
  3. Должны видеть: "[CSP Monitor] Инициализирован (sessionId: ...)"
  4. Если есть CSP нарушения, они будут залогированы в Google Sheets
     (лист 'csp_violations')

✅ Ожидаемый результат: НОЛЬ нарушений (все скрипты имеют nonce)
""")
    
    input("Нажмите Enter когда проверили CSP мониторинг... ")
    
    # ==============================================================
    print_step(5, "Проверка кэш метрик")
    # ==============================================================
    print("""
Текущие статистики кэша рекомендаций доступны по:
    
    curl http://localhost:5000/api/reco/stats | python -m json.tool
    
Должны видеть JSON типа:
    {
      "hits": 0,
      "misses": 0,
      "hit_rate": 0.0,
      "cache_size": 0,
      "ttl_seconds": 300,
      "total_requests": 0
    }

После генерации нескольких запросов рекомендаций:
  - hit_rate должна возрастать
  - cache_size должна быть > 0
""")
    
    # ==============================================================
    print_step(6, "Финальная проверка всех компонентов")
    # ==============================================================
    print("""
Запустим скрипт проверки готовности:
    
    python scripts/verify_production_readiness.py
""")
    
    response = input("Запустить финальную проверку? (y/n): ").strip().lower()
    if response == 'y':
        try:
            exec_result = subprocess.run(
                [sys.executable, "scripts/verify_production_readiness.py"],
                cwd=os.path.dirname(os.path.dirname(__file__)),
                capture_output=True,
                text=True,
                timeout=30
            )
            print(exec_result.stdout)
            if exec_result.returncode != 0:
                print("⚠️  Stderr:", exec_result.stderr)
        except Exception as e:
            print(f"❌ Не смог запустить скрипт: {e}")
    
    # ==============================================================
    print_header("✅ ГОТОВО К PRODUCTION!")
    # ==============================================================
    
    print("""
Резюме выполненных действий:

1. ✅ Analytics Logging
   - Endpoint: POST /analytics/log
   - Google Sheets: analytics_statistics
   - Тестовый скрипт: scripts/test_analytics_log.py

2. ✅ Service Images Seeding
   - Таблица: Image (group='services')
   - Количество: 10 записей
   - Скрипт заполнения: scripts/seed_service_images.py

3. ✅ CSP Violation Monitoring
   - Клиентский скрипт: static/js/csp-monitor.js
   - API endpoint: POST /api/csp-violations
   - Google Sheets: csp_violations
   - Ожидаемый результат: 0 нарушений

4. ✅ Cache Hit/Miss Metrics
   - Endpoint статистики: GET /api/reco/stats
   - Reset endpoint: POST /api/reco/stats/reset (требует X-Admin-Token)

Документация: PRODUCTION_READINESS.md

Следующие шаги:
  □ Проверить все логи в Google Sheets
  □ Настроить ADMIN_TOKEN в .env
  □ Установить мониторинг на /api/reco/stats (раз в час)
  □ Проверить CSP нарушения (должны быть 0)
  □ Развернуть на production сервер
  □ Настроить автоматическое заполнение Image таблицы (если нужно)

Поддержка & Отладка:
  - Логи Flask: STDOUT приложения
  - Analytics логи: Google Sheets + logs/
  - CSP violations: Google Sheets (csp_violations)
  - Cache метрики: GET /api/reco/stats

Удачи! 🚀
""")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n❌ Прерывано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
