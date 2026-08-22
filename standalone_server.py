import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

from domain import divide, get_item, get_user
from logger import logger
from settings import LOG_FILE


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
                self.wfile.write(b'event: log\ndata: {"message": "No log file available"}\n\n')
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
                self.wfile.write(b'event: log\ndata: {"message": "No error logs found"}\n\n')
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
                result = divide(int(query.get("a", [0])[0]), int(query.get("b", [0])[0]))
                self._send_json(200, {"result": result})
            elif path == "/users":
                self._send_json(200, {"user": get_user(query.get("id", [""])[0])})
            elif path == "/items":
                self._send_json(200, {"item": get_item(int(query.get("index", [0])[0]))})
            elif path == "/health":
                self._send_json(200, {"status": "healthy"})
            elif path == "/api/v1/projects/testapp/logs":
                self._stream_error_logs()
            else:
                self._send_json(404, {"error": "Not Found"})
        except Exception as exc:
            logger.exception("An error occurred while processing the request")
            self._send_json(500, {"error": str(exc)})

    def do_POST(self):
        path = urlparse(self.path).path
        logger.info(f"Received POST request for {path}")

        if path != "/api/v1/projects/testapp/logs":
            self._send_json(404, {"error": "Not Found"})
            return

        payload = self._validate_project_log_request()
        if payload is None:
            return

        for log_entry in payload["logs"]:
            logger.error("[%s] %s", payload["app_name"], log_entry)

        self._send_json(
            200,
            {
                "status": "accepted",
                "project_id": "testapp",
                "app_name": payload["app_name"],
                "received_logs": len(payload["logs"]),
            },
        )
