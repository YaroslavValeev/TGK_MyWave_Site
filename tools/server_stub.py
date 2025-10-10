"""
A tiny Python server to emulate the presence of the Node `server.js` for
local developer testing on machines without Node installed.

It exposes the same `/chat` POST endpoint and performs a no-op response.
This is only for local testing and demonstration.
"""
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os

HOST = '127.0.0.1'
PORT = int(os.getenv('DEV_SERVER_PORT', '5001'))

class Handler(BaseHTTPRequestHandler):
    def _set_headers(self, code=200):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_POST(self):
        if self.path != '/chat':
            self._set_headers(404)
            self.wfile.write(json.dumps({'error': 'not found'}).encode())
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length) if length else b''
        try:
            payload = json.loads(body.decode() or '{}')
        except Exception:
            payload = {}
        message = payload.get('message', '')
        # Return a deterministic placeholder reply for testing
        reply = f"(stub) received: {message[:200]}"
        self._set_headers(200)
        self.wfile.write(json.dumps({'reply': reply}).encode())

def run_server(host: str = HOST, port: int = PORT) -> None:
    """Run the stub server (blocking).

    Use this from tests or by direct invocation.
    """
    print(f"Starting dev server stub on http://{host}:{port} (POST /chat)")
    server = HTTPServer((host, port), Handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nShutting down')
        server.server_close()


if __name__ == '__main__':
    run_server()
