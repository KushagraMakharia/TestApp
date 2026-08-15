import json
import logging
import threading
import time
import urllib.request
from http.server import HTTPServer

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
