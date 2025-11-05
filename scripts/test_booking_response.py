import requests
import json

def test_booking():
    url = "http://localhost:5000/api/calendar/book"
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "name": "Тест",
        "phone": "+79123456789",
        "date": "2025-11-10",
        "time": "10:00"
    }
    
    response = requests.post(url, headers=headers, json=data)
    print(f"Статус: {response.status_code}")
    print(f"Ответ: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    test_booking()