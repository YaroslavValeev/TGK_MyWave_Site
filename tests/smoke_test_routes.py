"""
Smoke test для проверки основных маршрутов аналитики и других новых endpoints.
"""
import pytest
from app import create_app
import json


@pytest.fixture
def client():
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


def test_analytics_log_post_endpoint(client):
    """Проверяем, что POST /analytics/log доступен и возвращает 200."""
    payload = {
        "event": "reco_show",
        "context": "index",
        "label": "test",
        "timestamp": "2025-11-11T12:00:00Z",
        "user_key": "test_user"
    }
    response = client.post('/analytics/log', 
                          data=json.dumps(payload),
                          content_type='application/json')
    assert response.status_code in [200, 202]
    print(f"✅ POST /analytics/log returned {response.status_code}")


def test_analytics_log_requires_json(client):
    """Проверяем валидацию JSON в /analytics/log."""
    response = client.post('/analytics/log', 
                          data="invalid json",
                          content_type='application/json')
    # может быть 400 (bad request) или 500 (internal error при неправильном JSON)
    assert response.status_code in [400, 500]
    print(f"✅ POST /analytics/log rejects invalid JSON with {response.status_code}")


def test_sitemap_xml_route(client):
    """Проверяем, что /sitemap.xml возвращает валидный XML."""
    response = client.get('/sitemap.xml')
    assert response.status_code == 200
    assert 'application/xml' in response.content_type or 'text/xml' in response.content_type
    assert '<?xml' in response.get_data(as_text=True)
    print(f"✅ GET /sitemap.xml returned {response.status_code} with XML")


def test_calculator_save_endpoint(client):
    """Проверяем, что POST /api/calculator/save доступен."""
    payload = {
        "phone": "79991234567",
        "city": "Moscow",
        "tags": ["wakesurfing", "beginner"],
        "inputs": {"duration": 30},
        "result": {"price": 5000}
    }
    response = client.post('/api/calculator/save',
                          data=json.dumps(payload),
                          content_type='application/json')
    assert response.status_code in [200, 202]
    data = response.get_json()
    assert data.get('ok') == True
    print(f"✅ POST /api/calculator/save returned {response.status_code}")


def test_calculator_history_endpoint(client):
    """Проверяем, что GET /api/calculator/history доступен."""
    response = client.get('/api/calculator/history?phone=79991234567')
    assert response.status_code == 200
    data = response.get_json()
    assert 'ok' in data
    assert 'history' in data
    print(f"✅ GET /api/calculator/history returned {response.status_code}")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
