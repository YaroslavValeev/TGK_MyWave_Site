#!/usr/bin/env python3
"""
P0: Проверка формирования canonical_url после деплоя.

Проверяет, что canonical_url всегда формируется как https://mywavetreaning.ru/blog/{slug}
независимо от SERVER_NAME или других настроек.
"""
import sys
import os
import tempfile

# Устанавливаем переменные окружения для prometheus (если нужно)
if 'PROMETHEUS_MULTIPROC_DIR' not in os.environ:
    prometheus_dir = tempfile.mkdtemp()
    os.environ['PROMETHEUS_MULTIPROC_DIR'] = prometheus_dir

# Добавляем корень проекта в путь
repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, repo_root)

from app import create_app

def check_canonical_url():
    """Проверка формирования canonical_url."""
    print("=" * 60)
    print("P0: Проверка формирования canonical_url")
    print("=" * 60)
    
    # Создаём приложение в production режиме
    app = create_app('production')
    
    with app.app_context():
        from app.services.blog.publish import _get_public_blog_base_url, _make_canonical_url
        
        # Проверка 1: base_url
        print("\n1. Проверка base_url:")
        base_url = _get_public_blog_base_url()
        print(f"   Base URL: {base_url}")
        
        expected_base = "https://mywavetreaning.ru"
        if base_url == expected_base:
            print(f"   [OK] Соответствует ожидаемому: {expected_base}")
        else:
            print(f"   [ERROR] ОШИБКА: ожидается {expected_base}, получено {base_url}")
            return False
        
        # Проверка 2: canonical_url для разных slug
        print("\n2. Проверка canonical_url для разных slug:")
        test_slugs = [
            "test-post",
            "another-post-123",
            "post-with-special-chars-2026",
        ]
        
        all_ok = True
        for slug in test_slugs:
            canonical = _make_canonical_url(slug)
            expected = f"{expected_base}/blog/{slug}"
            if canonical == expected:
                print(f"   [OK] {slug} -> {canonical}")
            else:
                print(f"   [ERROR] {slug} -> {canonical} (ожидается {expected})")
                all_ok = False
        
        # Проверка 3: SERVER_NAME в конфиге
        print("\n3. Проверка SERVER_NAME в конфиге:")
        server_name = app.config.get("SERVER_NAME")
        if server_name:
            print(f"   SERVER_NAME установлен: {server_name}")
            print(f"   [WARN] Внимание: если SERVER_NAME != 'mywavetreaning.ru', canonical_url может быть неправильным")
        else:
            print(f"   SERVER_NAME не установлен (используется fallback)")
            print(f"   [OK] Fallback использует canonical домен: {expected_base}")
        
        # Проверка 4: Edge cases
        print("\n4. Проверка edge cases:")
        edge_cases = [
            ("", None),  # Пустой slug
            ("/blog/test", "https://mywavetreaning.ru/blog/blog/test"),  # Slug с префиксом
            ("test-slug/", "https://mywavetreaning.ru/blog/test-slug"),  # Slug с trailing slash
        ]
        
        for slug, expected_result in edge_cases:
            canonical = _make_canonical_url(slug)
            if expected_result is None:
                # Пустой slug должен вернуть None
                if canonical is None:
                    print(f"   [OK] Пустой slug -> None")
                else:
                    print(f"   [ERROR] Пустой slug -> {canonical} (ожидается None)")
                    all_ok = False
            else:
                if canonical == expected_result:
                    print(f"   [OK] '{slug}' -> {canonical}")
                else:
                    print(f"   [ERROR] '{slug}' -> {canonical} (ожидается {expected_result})")
                    all_ok = False
        
        print("\n" + "=" * 60)
        if all_ok:
            print("[SUCCESS] Все проверки пройдены успешно!")
            print("   canonical_url формируется корректно: https://mywavetreaning.ru/blog/{slug}")
            return True
        else:
            print("[FAIL] Обнаружены ошибки в формировании canonical_url")
            return False

if __name__ == "__main__":
    success = check_canonical_url()
    sys.exit(0 if success else 1)
