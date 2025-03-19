from typing import Optional
import logging
import datetime
from flask import request
from flask_socketio import SocketIO, emit, disconnect
from app.routes.calendar_routes import get_schedule_slots

# Add global connected_clients set
connected_clients = set()

class WebSocketHandler:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, websocket):
        # Store connection
        self.active_connections[id(websocket)] = websocket

    async def disconnect(self, websocket):
        # Remove connection
        if id(websocket) in self.active_connections:
            del self.active_connections[id(websocket)]

    async def handle_error(self, websocket, error):
        print(f"WebSocket error: {error}")
        await self.disconnect(websocket)

    def cleanup_user(self, sid):
        # Clean up any user-specific resources
        pass

# Вспомогательная функция для получения дня недели
def get_day_of_week(date_str):
    try:
        dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return dt.strftime("%A").lower()
    except Exception as e:
        logging.error(f"Ошибка получения дня недели: {e}")
        return None

def init_websocket(app):
    socketio = SocketIO(app)
    global connected_clients  # Add global reference
    
    @socketio.on('connect')
    def handle_connect():
        connected_clients.add(request.sid)
        print(f"Client connected. Total clients: {len(connected_clients)}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        connected_clients.discard(request.sid)
        print(f"Client disconnected. Total clients: {len(connected_clients)}")
    
    @socketio.on("request_slots")
    def handle_request_slots(data):
        """
        Обрабатывает запрос на получение слотов по дню недели.
        """
        selected_date = data.get("date")
        selected_day_of_week = get_day_of_week(selected_date) if selected_date else None
        
        if not selected_day_of_week:
            emit("update_slots", {"error": "Неверная или отсутствующая дата"})
            return
        
        slots = get_schedule_slots(selected_day_of_week)  # Получаем слоты по дню недели
        print(f"📡 WebSocket отправляет: {slots}")  # Логируем перед отправкой
        
        emit("update_slots", slots)
    
    # Example of broadcasting to all connected clients
    def broadcast_message(message):
        if connected_clients:
            emit('broadcast', message, broadcast=True)
    
    return socketio

ws_handler = WebSocketHandler()
