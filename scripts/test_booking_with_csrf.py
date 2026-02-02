import requests
import json

BASE = "http://127.0.0.1:5000"

s = requests.Session()
# Получаем CSRF токен
r = s.get(BASE + "/api/csrf-token")
print("GET /api/csrf-token", r.status_code)
data = r.json()
csrf = data.get("csrf_token")
print("csrf:", csrf)

headers = {"Content-Type": "application/json", "X-CSRFToken": csrf}

payload = {
    "name": "Тестовый пользователь",
    "phone": "+79123456789",
    "date": "2025-11-10",
    "time": "10:00",
}

resp = s.post(BASE + "/api/calendar/book", headers=headers, json=payload)
print("POST status", resp.status_code)
try:
    print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
except Exception as e:
    print("No json, text:", resp.text)
