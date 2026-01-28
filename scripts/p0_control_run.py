#!/usr/bin/env python3
"""
P0: Контрольный прогон после деплоя на проде.

Выполняет оба теста из docs/P0_CONTROL_RUN.md:
1. Успешный writeback с canonical_url
2. Safety-кейс: WP_ROW_NUMBER_MISSING

Требует:
- Доступ к Google Sheets API
- Настроенные переменные окружения (GOOGLE_SERVICE_ACCOUNT_FILE, SPREADSHEET_ID)
- Доступ к базе данных
"""
import sys
import os
from datetime import datetime

# Добавляем корень проекта в путь
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from app import create_app
from app.database import db
from app.services.blog.publish import (
    publish_ready_posts,
    record_publish_error_by_id,
    acquire_publish_lock,
    ack_publish,
)
from app.services.google import read_sheet
from app.services.parser_news_sheet import resolve_parser_source

def print_section(title):
    """Печать заголовка секции."""
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

def print_result(test_name, success, details=None):
    """Печать результата теста."""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"\n{status}: {test_name}")
    if details:
        for key, value in details.items():
            print(f"   {key}: {value}")

def test_1_successful_writeback():
    """
    Тест 1: Успешный writeback с canonical_url.
    
    Требования:
    - Найти запись со статусом READY_TO_PUBLISH
    - row_number валиден (>= 2)
    - published_posts != TRUE
    """
    print_section("ТЕСТ 1: Успешный writeback с canonical_url")
    
    app = create_app('production')
    with app.app_context():
        # Читаем таблицу
        spreadsheet_id, sheet_name = resolve_parser_source()
        records, headers = read_sheet(spreadsheet_id, sheet_name)
        
        # Ищем подходящую запись
        test_record = None
        for record in records:
            status = str(record.get("status", "")).strip()
            published = str(record.get("published_posts", "")).strip().upper()
            row_num = record.get("row_number")
            
            if (status == "READY_TO_PUBLISH" and 
                published not in ("TRUE", "1") and
                row_num and 
                isinstance(row_num, (int, str)) and 
                str(row_num).strip() and
                int(str(row_num).strip()) >= 2):
                test_record = record
                break
        
        if not test_record:
            print("⚠️  Не найдена подходящая запись для теста.")
            print("   Требования:")
            print("   - status = READY_TO_PUBLISH")
            print("   - published_posts != TRUE")
            print("   - row_number валиден (>= 2)")
            print("\n   Создайте тестовую запись вручную или используйте существующую.")
            return False, None
        
        # Данные для проверки
        sheet_id = test_record.get("id", "")
        row_number = int(str(test_record.get("row_number", "")).strip())
        slug = test_record.get("slug", "") or test_record.get("raw_title", "").lower().replace(" ", "-")
        
        print(f"Найдена тестовая запись:")
        print(f"   ID: {sheet_id}")
        print(f"   row_number: {row_number}")
        print(f"   slug: {slug}")
        print(f"   status: {test_record.get('status')}")
        print(f"   published_posts: {test_record.get('published_posts')}")
        
        # Запоминаем состояние "до"
        before = {
            "published_posts": test_record.get("published_posts", ""),
            "published_at": test_record.get("published_at", ""),
            "canonical_url": test_record.get("canonical_url", ""),
            "publish_error": test_record.get("publish_error", ""),
        }
        
        print(f"\nСостояние ДО:")
        for key, value in before.items():
            print(f"   {key}: {value}")
        
        # Запускаем публикацию
        print(f"\nЗапуск publish_ready_posts()...")
        stats = publish_ready_posts(db.session)
        print(f"Статистика: {stats}")
        
        # Читаем состояние "после"
        records_after, _ = read_sheet(spreadsheet_id, sheet_name)
        record_after = None
        for r in records_after:
            if str(r.get("id", "")).strip() == str(sheet_id).strip():
                record_after = r
                break
        
        if not record_after:
            print("❌ Запись не найдена после публикации")
            return False, None
        
        after = {
            "published_posts": record_after.get("published_posts", ""),
            "published_at": record_after.get("published_at", ""),
            "canonical_url": record_after.get("canonical_url", ""),
            "publish_error": record_after.get("publish_error", ""),
            "publish_attempts": record_after.get("publish_attempts", ""),
        }
        
        print(f"\nСостояние ПОСЛЕ:")
        for key, value in after.items():
            print(f"   {key}: {value}")
        
        # Проверки
        checks = {
            "published_posts = TRUE": after["published_posts"].upper() == "TRUE",
            "published_at заполнен": bool(after["published_at"]),
            "canonical_url заполнен": bool(after["canonical_url"]),
            "canonical_url правильный формат": (
                after["canonical_url"].startswith("https://mywavetreaning.ru/blog/") if after["canonical_url"] else False
            ),
            "publish_error пуст": not after["publish_error"] or after["publish_error"].strip() == "",
        }
        
        print(f"\nПроверки:")
        all_ok = True
        for check_name, check_result in checks.items():
            status_icon = "✅" if check_result else "❌"
            print(f"   {status_icon} {check_name}")
            if not check_result:
                all_ok = False
        
        # Формируем ссылку на строку
        sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?pli=1&gid=1039755742#gid=1039755742&range={row_number}:{row_number}"
        
        result_details = {
            "ID": sheet_id,
            "row_number": row_number,
            "canonical_url": after["canonical_url"],
            "Ссылка": sheet_url,
        }
        
        return all_ok, result_details

def test_2_row_number_missing():
    """
    Тест 2: Safety-кейс (WP_ROW_NUMBER_MISSING).
    
    Требования:
    - Создать запись без row_number или с невалидным row_number
    - Проверить, что writeback НЕ выполняется
    - Проверить, что publish_error = WP_ROW_NUMBER_MISSING
    """
    print_section("ТЕСТ 2: Safety-кейс (WP_ROW_NUMBER_MISSING)")
    
    app = create_app('production')
    with app.app_context():
        spreadsheet_id, sheet_name = resolve_parser_source()
        
        # Создаём тестовую запись без row_number
        test_id = f"site_p0_test_safety_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        print(f"Создание тестовой записи:")
        print(f"   ID: {test_id}")
        print(f"   row_number: (пусто)")
        print(f"   status: READY_TO_PUBLISH")
        
        # ВАЖНО: Этот тест требует ручного создания записи в таблице,
        # так как мы не можем напрямую добавлять строки через API без row_number.
        # Вместо этого ищем существующую запись без row_number или с невалидным.
        
        records, headers = read_sheet(spreadsheet_id, sheet_name)
        
        # Ищем запись без row_number или с невалидным
        test_record = None
        for record in records:
            row_num = record.get("row_number")
            status = str(record.get("status", "")).strip()
            
            # Проверяем, что row_number пуст или невалиден
            is_invalid = (
                not row_num or
                str(row_num).strip() == "" or
                (isinstance(row_num, (int, str)) and 
                 (not str(row_num).strip().isdigit() or int(str(row_num).strip()) < 2))
            )
            
            if is_invalid and status == "READY_TO_PUBLISH":
                test_record = record
                break
        
        if not test_record:
            print("⚠️  Не найдена запись без row_number для теста.")
            print("   Создайте вручную запись в таблице:")
            print(f"   - id: {test_id}")
            print("   - status: READY_TO_PUBLISH")
            print("   - row_number: (оставьте пустым или установите < 2)")
            print("   - raw_title: Test P0 Safety")
            print("\n   Затем запустите скрипт снова.")
            return False, None
        
        sheet_id = test_record.get("id", "")
        
        print(f"Найдена тестовая запись:")
        print(f"   ID: {sheet_id}")
        print(f"   row_number: {test_record.get('row_number', '(пусто)')}")
        print(f"   status: {test_record.get('status')}")
        
        # Запоминаем состояние "до"
        before = {
            "published_posts": test_record.get("published_posts", ""),
            "published_at": test_record.get("published_at", ""),
            "canonical_url": test_record.get("canonical_url", ""),
            "publish_error": test_record.get("publish_error", ""),
        }
        
        print(f"\nСостояние ДО:")
        for key, value in before.items():
            print(f"   {key}: {value}")
        
        # Запускаем публикацию
        print(f"\nЗапуск publish_ready_posts()...")
        stats = publish_ready_posts(db.session)
        print(f"Статистика: {stats}")
        
        # Читаем состояние "после"
        records_after, _ = read_sheet(spreadsheet_id, sheet_name)
        record_after = None
        for r in records_after:
            if str(r.get("id", "")).strip() == str(sheet_id).strip():
                record_after = r
                break
        
        if not record_after:
            print("❌ Запись не найдена после публикации")
            return False, None
        
        after = {
            "published_posts": record_after.get("published_posts", ""),
            "published_at": record_after.get("published_at", ""),
            "canonical_url": record_after.get("canonical_url", ""),
            "publish_error": record_after.get("publish_error", ""),
            "publish_attempts": record_after.get("publish_attempts", ""),
        }
        
        print(f"\nСостояние ПОСЛЕ:")
        for key, value in after.items():
            print(f"   {key}: {value}")
        
        # Проверки
        checks = {
            "published_posts НЕ изменился": after["published_posts"] == before["published_posts"],
            "published_at НЕ заполнен": not after["published_at"] or after["published_at"] == before["published_at"],
            "canonical_url НЕ заполнен": not after["canonical_url"] or after["canonical_url"] == before["canonical_url"],
            "publish_error = WP_ROW_NUMBER_MISSING или WP_ROW_NUMBER_INVALID": (
                "WP_ROW_NUMBER_MISSING" in str(after["publish_error"]) or
                "WP_ROW_NUMBER_INVALID" in str(after["publish_error"])
            ),
            "publish_attempts увеличен": (
                int(str(after["publish_attempts"]).strip() or "0") > 
                int(str(before.get("publish_attempts", "0")).strip() or "0")
            ),
        }
        
        print(f"\nПроверки:")
        all_ok = True
        for check_name, check_result in checks.items():
            status_icon = "✅" if check_result else "❌"
            print(f"   {status_icon} {check_name}")
            if not check_result:
                all_ok = False
        
        # Формируем ссылку на строку (если есть row_number, иначе по ID)
        row_num = record_after.get("row_number")
        if row_num and str(row_num).strip().isdigit():
            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?pli=1&gid=1039755742#gid=1039755742&range={row_num}:{row_num}"
        else:
            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit?pli=1&gid=1039755742#gid=1039755742"
        
        result_details = {
            "ID": sheet_id,
            "row_number": row_num or "(пусто)",
            "publish_error": after["publish_error"],
            "Ссылка": sheet_url,
        }
        
        return all_ok, result_details

def main():
    """Главная функция."""
    print("=" * 60)
    print("P0: Контрольный прогон после деплоя")
    print("=" * 60)
    print(f"Дата: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Тест 1
    try:
        success, details = test_1_successful_writeback()
        results["test_1"] = {"success": success, "details": details}
        print_result("Тест 1: Успешный writeback", success, details)
    except Exception as e:
        print(f"\n❌ Ошибка в тесте 1: {e}")
        import traceback
        traceback.print_exc()
        results["test_1"] = {"success": False, "error": str(e)}
    
    # Тест 2
    try:
        success, details = test_2_row_number_missing()
        results["test_2"] = {"success": success, "details": details}
        print_result("Тест 2: WP_ROW_NUMBER_MISSING", success, details)
    except Exception as e:
        print(f"\n❌ Ошибка в тесте 2: {e}")
        import traceback
        traceback.print_exc()
        results["test_2"] = {"success": False, "error": str(e)}
    
    # Итоги
    print_section("ИТОГИ")
    all_passed = all(r.get("success", False) for r in results.values())
    
    for test_name, result in results.items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        print(f"{status}: {test_name}")
        if "error" in result:
            print(f"   Ошибка: {result['error']}")
    
    if all_passed:
        print("\n✅ Все тесты пройдены успешно!")
        print("\nСледующий шаг: Зафиксировать результаты в docs/DECISION_LOG_R2_P0.md")
    else:
        print("\n❌ Некоторые тесты не прошли. Проверьте логи выше.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
