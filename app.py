import json
import logging
import os
import sys
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Set up logging to both stdout and a local log file
LOG_DIR = Path(__file__).resolve().parent
LOG_FILE = LOG_DIR / "app.log"

logger = logging.getLogger("test_application")
logger.setLevel(logging.DEBUG)

# Create file handler
fh = logging.FileHandler(str(LOG_FILE))
fh.setLevel(logging.DEBUG)

# Create formatter
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
logger.addHandler(fh)

# Also output to stdout
sh = logging.StreamHandler(sys.stdout)
sh.setFormatter(formatter)
logger.addHandler(sh)

USERS = {"1": "Alice", "2": "Bob"}
ITEMS = ["apple", "banana", "cherry"]

def divide(a: int, b: int) -> float:
    if b == 0:
        logger.warning("Division by zero attempted for %s / %s", a, b)
        return 0.0
    return a / b


def get_user(user_id: str) -> str:
    return USERS.get(user_id, "Unknown User")


def get_item(index: int) -> str:
    if index < 0 or index >= len(ITEMS):
        return "Unknown Item"
    return ITEMS[index]

class StandaloneRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - - {format % args}")

    def _send_json(self, status_code: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _stream_error_logs(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache, no-transform")
        self.send_header("Connection", "close")
        self.end_headers()
        self.close_connection = True

        try:
            if not LOG_FILE.exists():
                self.wfile.write(b"event: log\ndata: {\"message\": \"No log file available\"}\n\n")
                self.wfile.flush()
                return

            with LOG_FILE.open("r", encoding="utf-8", errors="replace") as log_handle:
                entries = log_handle.read().splitlines()

            error_lines = [
                line.strip()
                for line in entries
                if any(level in line.upper() for level in ("ERROR", "CRITICAL", "EXCEPTION"))
            ]

            if not error_lines:
                self.wfile.write(b"event: log\ndata: {\"message\": \"No error logs found\"}\n\n")
                self.wfile.flush()
                return

            for line in error_lines[-50:]:
                payload = json.dumps({"message": line})
                self.wfile.write(f"event: error\ndata: {payload}\n\n".encode("utf-8"))
                self.wfile.flush()
        except Exception as exc:
            logger.exception("Failed to stream logs")
            self.wfile.write(
                f"event: error\ndata: {json.dumps({'message': str(exc)})}\n\n".encode("utf-8")
            )
            self.wfile.flush()

    def _validate_project_log_request(self):
        project_id = self.headers.get("project_id")
        if project_id != "testapp":
            self._send_json(400, {"error": "project_id header must be 'testapp'"})
            return None

        length = self.headers.get("Content-Length")
        if length is None:
            self._send_json(400, {"error": "Request body is required"})
            return None

        try:
            raw = self.rfile.read(int(length))
            payload = json.loads(raw.decode("utf-8"))
        except (ValueError, TypeError, UnicodeDecodeError):
            self._send_json(400, {"error": "Request body must be valid JSON"})
            return None

        if not isinstance(payload, dict):
            self._send_json(400, {"error": "Request body must be an object"})
            return None

        app_name = payload.get("app_name")
        logs = payload.get("logs")
        if app_name != "default":
            self._send_json(400, {"error": "app_name must be 'default'"})
            return None
        if not isinstance(logs, list) or not all(isinstance(item, str) for item in logs):
            self._send_json(400, {"error": "logs must be an array of strings"})
            return None

        return {"app_name": app_name, "logs": logs}

    def do_GET(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)

        logger.info(f"Received request for {path}")

        try:
            if path == "/calculate":
                a = int(query.get("a", [0])[0])
                b = int(query.get("b", [0])[0])
                result = divide(a, b)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(f'{{"result": {result}}}'.encode("utf-8"))

            elif path == "/users":
                user_id = query.get("id", [""])[0]
                user = get_user(user_id)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(f'{{"user": "{user}"}}'.encode("utf-8"))

            elif path == "/items":
                idx = int(query.get("index", [0])[0])
                item = get_item(idx)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(f'{{"item": "{item}"}}'.encode("utf-8"))

            elif path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "healthy"}')

            elif path == "/api/v1/projects/testapp/logs":
                self._stream_error_logs()

            else:
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")

        except Exception as e:
            logger.exception("An error occurred while processing the request")
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"error": "{str(e)}"}}'.encode("utf-8"))

    def do_POST(self):
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        logger.info(f"Received POST request for {path}")

        if path == "/api/v1/projects/testapp/logs":
            payload = self._validate_project_log_request()
            if payload is None:
                return

            for log_entry in payload["logs"]:
                logger.error("[%s] %s", payload["app_name"], log_entry)

            self._send_json(200, {
                "status": "accepted",
                "project_id": "testapp",
                "app_name": payload["app_name"],
                "received_logs": len(payload["logs"]),
            })
            return

        self._send_json(404, {"error": "Not Found"})

def run_server(port=8080):
    server_address = ("", port)
    httpd = HTTPServer(server_address, StandaloneRequestHandler)
    logger.info(f"Starting test application server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping test application server...")
        httpd.server_close()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    run_server(port=port)
