"""A tiny in-process HTTP server used as a test double."""
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, status, payload, content_type="application/json"):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {"status": "ok", "version": "1.2.0"})
        elif self.path == "/users":
            self._send(200, {"items": [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]})
        elif self.path == "/slow":
            time.sleep(0.3)
            self._send(200, {"status": "ok"})
        elif self.path == "/text":
            self._send(200, b"hello plain world", "text/plain")
        elif self.path == "/auth":
            ok = self.headers.get("Authorization") == "Bearer secret-token"
            self._send(200 if ok else 401, {"authorized": ok})
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = json.loads(self.rfile.read(length) or b"{}")
        self._send(201, {"created": True, "echo": data, "type": self.headers.get("Content-Type")})


class TestServer:
    def __enter__(self):
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}"
        return self

    def __exit__(self, *exc):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)
