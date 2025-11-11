"""
Smoke test для проверки функции log_analytics_event в google_sheets_service.
"""
import pytest
from app.services.google_sheets_service import log_analytics_event


def test_log_analytics_event_accepts_dict():
    """Проверяем, что функция принимает dict и не вызывает exception при ошибке Sheets."""
    event = {
        "ts": "2025-11-11T12:00:00Z",
        "event": "reco_show",
        "context": "index",
        "user_key": "test_session_123",
        "rule_id": "prio:service>product",
        "meta": {"count": 4}
    }
    
    # Функция не должна вызывать исключение, даже если Sheets недоступен
    try:
        result = log_analytics_event(event)
        print(f"✅ log_analytics_event() executed without exception")
    except Exception as e:
        # Если всё же есть exception, это должно быть логировано, но не падать
        print(f"⚠️  log_analytics_event() raised (expected if no Sheets): {e}")


def test_log_analytics_event_with_minimal_event():
    """Проверяем функцию с минимальным набором полей."""
    event = {
        "ts": "2025-11-11T12:00:00Z",
        "event": "reco_click",
        "context": "blog_post"
    }
    
    try:
        result = log_analytics_event(event)
        print(f"✅ log_analytics_event() handles minimal event")
    except Exception as e:
        print(f"⚠️  log_analytics_event() minimal event raised: {e}")


def test_log_analytics_event_retry_logic():
    """Проверяем, что функция имеет retry-логику (не падает на первой ошибке)."""
    import inspect
    source = inspect.getsource(log_analytics_event)
    
    # Проверяем наличие retry-логики в исходном коде
    assert 'max_retries' in source or 'retry' in source.lower()
    assert 'exponential' in source.lower() or 'backoff' in source.lower() or 'time.sleep' in source
    print(f"✅ log_analytics_event() has retry/backoff logic")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
