import json
import logging
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
import httpx

LOG_DIR = Path(__file__).resolve().parent
LOG_FILE = LOG_DIR / "app.log"

logger = logging.getLogger("test_application")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(str(LOG_FILE))
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

USERS = {"1": "Alice", "2": "Bob"}
ITEMS = ["apple", "banana", "cherry"]


def divide(a: int, b: int) -> float:
    return a / b


def get_user(user_id: str) -> str:
    return USERS.get(str(user_id), "Unknown User")


def get_item(index: int) -> str:
    if not isinstance(index, int):
        try:
            index = int(index)
        except (TypeError, ValueError):
            return "Unknown Item"

    if 0 <= index < len(ITEMS):
        return ITEMS[index]
    return "Unknown Item"


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

            self._send_json(
                200,
                {
                    "status": "accepted",
                    "project_id": "testapp",
                    "app_name": payload["app_name"],
                    "received_logs": len(payload["logs"]),
                },
            )
            return

        self._send_json(404, {"error": "Not Found"})


def _read_log_errors() -> list[str]:
    if not LOG_FILE.exists():
        return []
    with LOG_FILE.open("r", encoding="utf-8", errors="replace") as log_handle:
        entries = log_handle.read().splitlines()
    return [
        line.strip()
        for line in entries
        if any(level in line.upper() for level in ("ERROR", "CRITICAL", "EXCEPTION"))
    ][-50:]


async def send_error_to_webhook(error_type: str, error_message: str, error_traceback: str):
    """Send error traceback to the webhook endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                "http://127.0.0.1:8000/api/v1/projects/testapp/webhook",
                json={
                    "error_type": error_type,
                    "error_message": error_message,
                    "traceback": error_traceback,
                },
                timeout=5.0,
            )
    except Exception as e:
        logger.error(f"Failed to send error to webhook: {e}")


app = FastAPI(title="Standalone Target Test Application")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch all exceptions and send them to the webhook."""
    error_type = type(exc).__name__
    error_message = str(exc)
    error_traceback = traceback.format_exc()
    
    logger.error(f"Exception caught: {error_type} - {error_message}\n{error_traceback}")
    
    # Send error to webhook
    await send_error_to_webhook(error_type, error_message, error_traceback)
    
    return {
        "detail": "Internal server error",
        "error_type": error_type,
        "error_message": error_message,
    }, 500


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.get("/calculate")
async def calculate(a: int = Query(...), b: int = Query(...)) -> dict:
    return {"result": divide(a, b)}


@app.get("/users")
async def users(user_id: str = Query(..., alias="id")) -> dict:
    user = get_user(user_id)
    return {"user": user}


@app.get("/items")
async def items(index: int = Query(...)) -> dict:
    item = get_item(index)
    return {"item": item}


@app.get("/api/v1/projects/testapp/logs")
async def project_logs_stream() -> StreamingResponse:
    def event_generator():
        error_lines = _read_log_errors()
        if not error_lines:
            yield 'event: log\ndata: {"message": "No error logs found"}\n\n'
            return

        for line in error_lines:
            yield f"event: error\ndata: {json.dumps({'message': line})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache, no-transform", "Connection": "close"},
    )


@app.post("/api/v1/projects/testapp/logs")
async def project_logs_post(
    request: Request,
    project_id: str | None = Header(default=None, alias="project_id"),
):
    payload = await request.json()

    app_name = payload.get("app_name")
    logs = payload.get("logs")

    for log_entry in logs:
        logger.error("[%s] %s", app_name, log_entry)

    return {
        "status": "accepted",
        "project_id": "testapp",
        "app_name": app_name,
        "received_logs": len(logs),
    }


@app.post("/api/v1/projects/testapp/webhook")
async def webhook_endpoint(request: Request) -> dict:
    """Receive error tracebacks from the exception handler."""
    payload = await request.json()
    
    error_type = payload.get("error_type")
    error_message = payload.get("error_message")
    error_traceback = payload.get("traceback")
    
    logger.error(f"Webhook received error: {error_type} - {error_message}")
    logger.error(f"Traceback:\n{error_traceback}")
    
    return {
        "status": "received",
        "error_type": error_type,
    }


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
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting test application server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

