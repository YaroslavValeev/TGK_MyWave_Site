import asyncio
from flask import Flask, request, render_template
from flask_socketio import SocketIO
from websocket_handler import ws_handler
from geventwebsocket.handler import WebSocketHandler
from gevent.pywsgi import WSGIServer

app = Flask(__name__)
socketio = SocketIO(app)

# Add global set for connected clients
connected_clients = set()

@socketio.on('connect')
def handle_connect():
    global connected_clients
    connected_clients.add(request.sid)
    print(f"🔌 WebSocket client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect(sid):
    global connected_clients
    connected_clients.discard(sid)
    print(f'Client disconnected: {sid}')
    try:
        ws_handler.cleanup_user(sid)
    except Exception as e:
        print(f'Error during disconnect cleanup: {e}')

async def websocket_endpoint(websocket):
    try:
        await ws_handler.connect(websocket)
        while True:
            try:
                data = await websocket.receive_text()
                # Handle received data
            except Exception as e:
                await ws_handler.handle_error(websocket, e)
                break
    finally:
        await ws_handler.disconnect(websocket)

@app.route('/')
def home():
    return render_template('index.html')

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    http_server = WSGIServer(('', 5000), app, handler_class=WebSocketHandler)
    http_server.serve_forever()
