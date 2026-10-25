import json
import logging
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, HTTPServer

from app import StandaloneRequestHandler, divide, get_item, get_user


def test_divide_success():
    assert divide(10, 2) == 5.0


def test_divide_by_zero():
    # Expected behavior: return 0.0 when dividing by zero to avoid crash
    assert divide(10, 0) == 0.0


def test_get_user_success():
    assert get_user("1") == "Alice"


def test_get_user_failure():
    # Expected behavior: return "Unknown User" for non-existent users
    assert get_user("999") == "Unknown User"


def test_get_item_success():
    assert get_item(1) == "banana"


def test_get_item_failure():
    # Expected behavior: return "Unknown Item" for out-of-bound indices
    assert get_item(999) == "Unknown Item"


def test_logs_endpoint_streams_errors():
    server = HTTPServer(("127.0.0.1", 0), StandaloneRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        log_message = f"ERROR - streamed test log {time.time()}"
        logging.getLogger("test_application").error(log_message)

        with urllib.request.urlopen(
            f"http://127.0.0.1:{server.server_address[1]}/api/v1/projects/testapp/logs",
            timeout=5,
        ) as response:
            body = response.read().decode("utf-8")
            assert response.headers.get_content_type() == "text/event-stream"

        assert log_message in body
    finally:
        server.shutdown()
        server.server_close()


def test_logs_endpoint_streams_all_logs():
    server = HTTPServer(("127.0.0.1", 0), StandaloneRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        info_message = f"INFO - streamed info test log {time.time()}"
        logging.getLogger("test_application").info(info_message)

        with urllib.request.urlopen(
            f"http://127.0.0.1:{server.server_address[1]}/api/v1/projects/testapp/logs",
            timeout=5,
        ) as response:
            body = response.read().decode("utf-8")
            assert response.headers.get_content_type() == "text/event-stream"

        assert info_message in body
    finally:
        server.shutdown()
        server.server_close()


def test_logs_endpoint_accepts_required_project_header_and_schema():
    server = HTTPServer(("127.0.0.1", 0), StandaloneRequestHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        payload = json.dumps({"app_name": "default", "logs": ["first error", "second error"]}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{server.server_address[1]}/api/v1/projects/testapp/logs",
            data=payload,
            headers={"Content-Type": "application/json", "project_id": "testapp"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
            assert response.status == 200
            assert body["project_id"] == "testapp"
            assert body["app_name"] == "default"
            assert body["received_logs"] == 2
    finally:
        server.shutdown()
        server.server_close()


def test_http_log_stream_handler():
    from logger import HttpLogStreamHandler

    received = []

    class MockLogServer(BaseHTTPRequestHandler):
        def do_POST(self):
            length = int(self.headers.get("Content-Length", 0))
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            received.append(
                {
                    "payload": payload,
                    "key": self.headers.get("X-AutoCure-Ingestion-Key"),
                }
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status": "ok"}')

        def log_message(self, *args):
            pass

    mock_server = HTTPServer(("127.0.0.1", 0), MockLogServer)
    mock_port = mock_server.server_address[1]
    thread = threading.Thread(target=mock_server.serve_forever, daemon=True)
    thread.start()

    try:
        handler = HttpLogStreamHandler(
            endpoint_url=f"http://127.0.0.1:{mock_port}/api/v1/projects/testapp/logs",
            ingestion_key="test-key",
            app_name="testapp",
            flush_interval=0.05,
        )
        test_logger = logging.getLogger("test_stream_mock")
        test_logger.setLevel(logging.INFO)
        test_logger.addHandler(handler)

        test_logger.info("Sample streaming log line 1")
        test_logger.warning("Sample streaming log line 2")
        handler.flush()

        assert len(received) >= 1
        all_logs = []
        for r in received:
            all_logs.extend(r["payload"]["logs"])
        assert any("Sample streaming log line 1" in line for line in all_logs)
        assert any("Sample streaming log line 2" in line for line in all_logs)
        assert received[0]["key"] == "test-key"
        handler.close()
    finally:
        mock_server.shutdown()
        mock_server.server_close()
