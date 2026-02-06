import pytest

# Тесты для метрик кэша рекомендаций.
# Сделаны минимально зависимыми от Flask: работаем с внутренними глобальными счётчиками.
from app.services import recommendations_service as rs


def test_cache_metrics_hit_and_miss_unitary():
    # Сбрасываем счётчики напрямую
    rs.reset_cache_stats()

    # Начальные счётчики
    assert getattr(rs, "_CACHE_HITS", 0) == 0
    assert getattr(rs, "_CACHE_MISSES", 0) == 0

    # Ключ отсутствует -> промах
    val = rs._cache_get("nonexistent:key")
    assert val is None
    assert getattr(rs, "_CACHE_MISSES", 0) >= 1

    # Ставим значение в кэш
    rs._cache_set("test:key", [{"id": "x"}])

    # Попадание
    got = rs._cache_get("test:key")
    assert got is not None
    assert getattr(rs, "_CACHE_HITS", 0) >= 1

    # Сброс считается рабочим
    rs.reset_cache_stats()
    assert getattr(rs, "_CACHE_HITS", 0) == 0
    assert getattr(rs, "_CACHE_MISSES", 0) == 0
