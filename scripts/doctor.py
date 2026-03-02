#!/usr/bin/env python3
"""
Doctor — быстрая диагностика окружения проекта MyWave.

Проверяет без запуска приложения:
- Python и окружение
- Ключевые файлы и зависимости
- Переменные окружения (только факт наличия, без вывода значений)
- Файл сервисного аккаунта Google (опционально)

Использование:
    python scripts/doctor.py           # только лёгкие проверки
    python scripts/doctor.py --full    # + инициализация app, БД, Redis, health endpoint
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# Корень репозитория в PYTHONPATH для импорта app
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


def ok(msg: str) -> bool:
    print(f"  ✅ {msg}")
    return True


def fail(msg: str) -> bool:
    print(f"  ❌ {msg}")
    return False


def warn(msg: str) -> bool:
    print(f"  ⚠️  {msg}")
    return True


def section(title: str) -> None:
    print(f"\n{'='*50}")
    print(f"  {title}")
    print(f"{'='*50}")


def run_light_checks() -> bool:
    """Проверки без импорта app (быстро)."""
    all_ok = True

    section("Python и окружение")
    v = sys.version_info
    if v.major >= 3 and v.minor >= 8:
        all_ok &= ok(f"Python {v.major}.{v.minor}.{v.micro}")
    else:
        all_ok &= fail(f"Требуется Python 3.8+, сейчас {v.major}.{v.minor}.{v.micro}")

    cwd = Path.cwd()
    if REPO_ROOT == cwd or REPO_ROOT in cwd.parents:
        all_ok &= ok(f"Рабочая директория: {cwd}")
    else:
        all_ok &= warn(f"Запуск не из корня репо: {cwd} (репо: {REPO_ROOT})")

    section("Файлы проекта")
    req = REPO_ROOT / "requirements.txt"
    if req.is_file():
        all_ok &= ok(f"requirements.txt найден")
    else:
        all_ok &= fail("requirements.txt не найден")

    app_init = REPO_ROOT / "app" / "__init__.py"
    if app_init.is_file():
        all_ok &= ok("app/__init__.py найден")
    else:
        all_ok &= fail("app/__init__.py не найден")

    section("Переменные окружения (наличие)")
    # Критичные для прода и часто для разработки
    env_checks = [
        ("SECRET_KEY", True),
        ("GOOGLE_SERVICE_ACCOUNT_FILE", False),  # может быть файл по умолчанию
    ]
    for name, required in env_checks:
        val = os.environ.get(name)
        if val and len(val.strip()) > 0:
            all_ok &= ok(f"{name} задана")
        elif required:
            all_ok &= fail(f"{name} не задана")
        else:
            all_ok &= warn(f"{name} не задана (может использоваться значение по умолчанию)")

    # Сервисный аккаунт: без импорта app — только env и типичные пути
    section("Google Service Account")
    env_path = os.environ.get("GOOGLE_SERVICE_ACCOUNT_FILE")
    if env_path and Path(env_path).is_file():
        all_ok &= ok(f"Файл найден (из env): {env_path}")
    else:
        config_dir = REPO_ROOT / "configs"
        default_paths = [
            config_dir / "service_account.json",
            REPO_ROOT / "instance" / "service_account.json",
            REPO_ROOT / "service_account.json",
        ]
        found = next((p for p in default_paths if p.is_file()), None)
        if found:
            all_ok &= ok(f"Файл найден: {found}")
        else:
            if env_path:
                all_ok &= fail(f"Файл не найден: {env_path}")
            else:
                all_ok &= warn("Файл service_account.json не найден в configs/, instance/, корне")

    return all_ok


def run_full_checks() -> bool:
    """Проверки с созданием app (БД, Redis, health)."""
    all_ok = run_light_checks()

    section("Приложение и зависимости")
    try:
        from app import create_app  # noqa: F401
        app = create_app()
        all_ok &= ok("create_app() выполнен")
    except Exception as e:
        all_ok &= fail(f"create_app() ошибка: {e}")
        return all_ok

    section("База данных")
    with app.app_context():
        try:
            from flask import current_app
            from app.database.models import db
            uri = current_app.config.get("SQLALCHEMY_DATABASE_URI") or ""
            if not uri:
                all_ok &= warn("SQLALCHEMY_DATABASE_URI не задан")
            else:
                db.session.execute(db.text("SELECT 1"))
                all_ok &= ok("Подключение к БД успешно")
        except Exception as e:
            all_ok &= fail(f"БД: {e}")

    section("Redis (если настроен)")
    with app.app_context():
        from flask import current_app
        redis_url = (
            current_app.config.get("REDIS_URL")
            or current_app.config.get("AI_GATEWAY_REDIS_URL")
        )
        if not redis_url:
            all_ok &= warn("REDIS_URL / AI_GATEWAY_REDIS_URL не заданы")
        else:
            try:
                import redis
                r = redis.from_url(redis_url)
                r.ping()
                all_ok &= ok("Redis ping успешен")
            except Exception as e:
                all_ok &= fail(f"Redis: {e}")

    section("Health endpoint (локально)")
    try:
        import urllib.request
        # Проверяем только если сервер может быть поднят отдельно
        req = urllib.request.Request("http://127.0.0.1:5000/api/health", method="GET")
        with urllib.request.urlopen(req, timeout=2) as resp:
            if resp.status == 200:
                all_ok &= ok("GET /api/health → 200")
            else:
                all_ok &= warn(f"GET /api/health → {resp.status}")
    except OSError as e:
        all_ok &= warn(f"Сервер не запущен или недоступен: {e}")

    return all_ok


def main() -> int:
    parser = argparse.ArgumentParser(description="Диагностика окружения MyWave")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Дополнительно: app, БД, Redis, health endpoint",
    )
    args = parser.parse_args()

    print("\n🩺 Doctor — проверка окружения MyWave\n")
    success = run_full_checks() if args.full else run_light_checks()
    print()
    if success:
        print("✅ Все проверки пройдены.")
        return 0
    print("❌ Есть ошибки. Исправьте отмеченные пункты выше.")
    print("   Подсказка: для разработки задайте SECRET_KEY в .env или экспортируйте в оболочке.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
