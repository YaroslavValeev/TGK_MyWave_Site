from typing import Optional
import logging
import datetime
from flask import request, current_app
from flask_socketio import emit, disconnect
from app.routes.calendar_routes import get_available_slots
from app.extensions import socketio  # ✅ используем общий экземпляр

# Глобальный набор подключенных клиентов
connected_clients = set()

class WebSocketHandler:
    def __init__(self):
        self.active_connections = {}

    def connect(self, websocket):
        self.active_connections[id(websocket)] = websocket

    def disconnect(self, websocket):
        if id(websocket) in self.active_connections:
            del self.active_connections[id(websocket)]

    def handle_error(self, websocket, error):
        logging.error(f"WebSocket error: {error}")
        self.disconnect(websocket)

    def cleanup_user(self, sid):
        if sid in self.active_connections:
            self.disconnect(self.active_connections[sid])

# Вспомогательная функция
def get_day_of_week(date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%A").lower()
    except Exception as e:
        logging.error(f"Ошибка получения дня недели: {e}")
        return None

# ✅ Подключаем события
@socketio.on('connect')
def handle_connect():
    current_app.logger.info(f"WebSocket: подключение от клиента {request.sid}")
    connected_clients.add(request.sid)
    print(f"Client connected. Total clients: {len(connected_clients)}")

@socketio.on('disconnect')
def handle_disconnect():
    current_app.logger.info(f"WebSocket: отключение клиента {request.sid}")
    connected_clients.discard(request.sid)
    print(f"Client disconnected. Total clients: {len(connected_clients)}")

@socketio.on("request_slots")
def handle_request_slots(data):
    current_app.logger.info(f"WebSocket: запрос слотов от клиента {request.sid}")
    selected_date = data.get("date")
    selected_day_of_week = get_day_of_week(selected_date) if selected_date else None

    if not selected_day_of_week:
        emit("update_slots", {"error": "Неверная или отсутствующая дата"})
        return

    slots = get_available_slots(selected_date)
    print(f"📡 WebSocket отправляет: {slots}")
    emit("update_slots", slots)

def broadcast_message(message):
    if connected_clients:
        current_app.logger.info(f"WebSocket: широковещательное сообщение для {len(connected_clients)} клиентов")
        emit('broadcast', message, broadcast=True)

# Экземпляр класса (если используется где-то ещё)
ws_handler = WebSocketHandler()
