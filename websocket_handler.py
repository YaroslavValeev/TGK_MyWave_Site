from typing import Optional
import logging
from flask import request
from flask_socketio import emit, disconnect
from app.extensions import socketio

# Инициализация SocketIO

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

def init_websocket(app):
    socketio.init_app(app)  # Инициализация с приложением Flask
    global connected_clients  # Add global reference
    
    @socketio.on('connect')
    def handle_connect():
        connected_clients.add(request.sid)
        print(f"Client connected. Total clients: {len(connected_clients)}")
    
    @socketio.on('disconnect')
    def handle_disconnect():
        connected_clients.discard(request.sid)
        print(f"Client disconnected. Total clients: {len(connected_clients)}")
    
    # Example of broadcasting to all connected clients
    def broadcast_message(message):
        if connected_clients:
            emit('broadcast', message, broadcast=True)
    
    @socketio.on('message')
    def handle_message(data):
        print(f"Received message: {data}")
        # Обработка сообщения и, возможно, отправка ответа
        emit('response', {'data': 'Message received!'})
    
    return socketio

ws_handler = WebSocketHandler()
