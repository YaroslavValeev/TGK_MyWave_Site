def test_book_endpoint(client):
    response = client.post('/api/book', json={'name': 'Иван', 'date': '2024-07-01'})
    assert response.status_code == 200
    assert response.json['success'] 