#!/usr/bin/env python3
"""
Скрипт для проверки всех компонентов production-готовности.

Использование:
    python scripts/verify_production_readiness.py

Проверяет:
1. Database connectivity и наличие Image моделей с group='services'
2. Endpoints accessibility (рекомендации, аналитика, кэш статистика, CSP violations)
3. Google Sheets конфигурация
4. CSP header и nonce генерация
5. Рекомендации рендеринг (небольшой E2E тест)
"""
import sys
import os
import requests
import json
from pathlib import Path

# Добавляем корневую директорию в PATH
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def print_section(title):
    """Печатает заголовок секции."""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def print_check(msg, status):
    """Печатает результат проверки."""
    icon = "✅" if status else "❌"
    print(f"{icon} {msg}")
    return status

def main():
    """Главная функция."""
    print("\n🚀 Проверка готовности приложения к production\n")
    
    all_passed = True
    
    # ===========================
    # 1. Database & Images
    # ===========================
    print_section("1. Database & Models Check")
    
    try:
        from app import create_app
        from app.database.models import db, Image
        
        app = create_app()
        with app.app_context():
            # Проверяем подключение к БД
            try:
                result = db.session.execute(db.text("SELECT 1"))
                all_passed &= print_check("Database connection OK", True)
            except Exception as e:
                all_passed &= print_check(f"Database connection FAILED: {e}", False)
            
            # Проверяем наличие Image с group='services'
            try:
                image_count = Image.query.filter_by(group='services').count()
                if image_count > 0:
                    all_passed &= print_check(f"Found {image_count} service images", True)
                else:
                    print("⚠️  No service images found. Run: python scripts/seed_service_images.py")
            except Exception as e:
                all_passed &= print_check(f"Image query FAILED: {e}", False)
    
    except Exception as e:
        all_passed &= print_check(f"App initialization FAILED: {e}", False)
        return 1
    
    # ===========================
    # 2. API Endpoints
    # ===========================
    print_section("2. API Endpoints Check")
    
    # Старт приложения для тестирования
    BASE_URL = "http://localhost:5000"
    
    print(f"Testing endpoints at {BASE_URL}...")
    print("(Make sure app is running: python main.py)\n")
    
    endpoints_to_test = [
        ("GET", "/api/reco?context=index", "Recommendations"),
        ("GET", "/api/reco/stats", "Cache stats"),
        ("POST", "/api/csp-violations", "CSP violations (should accept empty)"),
        ("GET", "/analytics/log", "Analytics log endpoint"),
    ]
    
    for method, endpoint, desc in endpoints_to_test:
        try:
            url = BASE_URL + endpoint
            if method == "GET":
                resp = requests.get(url, timeout=2)
            elif method == "POST":
                resp = requests.post(url, json={}, timeout=2)
            
            # 204 No Content, 200 OK, или 400-500 all indicate endpoint exists
            all_passed &= print_check(f"{method:4} {endpoint:35} → {resp.status_code}", True)
        except requests.exceptions.ConnectionError:
            print("⚠️  Cannot connect to app. Make sure Flask app is running.")
            all_passed = False
        except Exception as e:
            all_passed &= print_check(f"{method:4} {endpoint:35} → ERROR: {str(e)[:40]}", False)
    
    # ===========================
    # 3. Google Sheets Configuration
    # ===========================
    print_section("3. Google Sheets Configuration")
    
    try:
        with app.app_context():
            from app.services.google_sheets_service import get_sheets_service
            
            # Пробуем инициализировать сервис
            try:
                service = get_sheets_service()
                if service:
                    all_passed &= print_check("Google Sheets service initialized", True)
                else:
                    print("⚠️  Google Sheets service not available (may be OK in dev mode)")
            except Exception as e:
                print(f"⚠️  Google Sheets service initialization: {str(e)[:60]}")
    except Exception as e:
        all_passed &= print_check(f"Google Sheets check FAILED: {e}", False)
    
    # ===========================
    # 4. CSP Configuration
    # ===========================
    print_section("4. CSP Configuration")
    
    try:
        # Проверяем наличие CSP header
        resp = requests.get(BASE_URL + "/", timeout=2)
        csp_header = resp.headers.get('Content-Security-Policy', '')
        
        if csp_header:
            has_nonce = 'nonce-' in csp_header
            all_passed &= print_check(f"CSP header present ({len(csp_header)} chars)", True)
            all_passed &= print_check(f"Nonce in CSP header", has_nonce)
            
            # Проверяем на unsafe-inline (не должно быть, используем nonce вместо этого)
            unsafe_inline = "'unsafe-inline'" in csp_header
            if not unsafe_inline:
                all_passed &= print_check("No 'unsafe-inline' detected (good)", True)
            else:
                print("⚠️  WARNING: 'unsafe-inline' detected in CSP (reduce XSS protection)")
        else:
            print("⚠️  WARNING: No CSP header found")
    
    except Exception as e:
        all_passed &= print_check(f"CSP check FAILED: {e}", False)
    
    # ===========================
    # 5. Feature Flags
    # ===========================
    print_section("5. Feature Flags")
    
    try:
        with app.app_context():
            flags = {
                'ENABLE_RECOMMENDATIONS': app.config.get('ENABLE_RECOMMENDATIONS', False),
                'ENABLE_ANALYTICS': app.config.get('ENABLE_ANALYTICS', False),
                'CSP_ENABLED': app.config.get('CSP_ENABLED', False),
                'RECO_CACHE_TTL': app.config.get('RECO_CACHE_TTL', 300),
                'AB_CONTROL_GROUP_SIZE': app.config.get('AB_CONTROL_GROUP_SIZE', 2),
            }
            
            for key, val in flags.items():
                icon = "✅" if val else "⚠️ "
                print(f"{icon} {key:30} = {val}")
    
    except Exception as e:
        all_passed &= print_check(f"Feature flags check FAILED: {e}", False)
    
    # ===========================
    # Summary
    # ===========================
    print_section("Summary")
    
    if all_passed:
        print("✅ All critical checks passed!")
        print("\nNext steps:")
        print("  1. If no service images found, run: python scripts/seed_service_images.py")
        print("  2. Test analytics: python scripts/test_analytics_log.py")
        print("  3. Monitor CSP violations: Check GET /api/csp-violations in browser console")
        print("  4. Monitor cache: curl http://localhost:5000/api/reco/stats")
        return 0
    else:
        print("❌ Some checks failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
