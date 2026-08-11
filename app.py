import logging
import os
import sys
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
    # INTENTIONAL BUG: division by zero if b is 0.
    # To fix: check if b == 0 and return 0.0 or raise ValueError.
    return a / b

def get_user(user_id: str) -> str:
    # INTENTIONAL BUG: KeyError if user_id not in USERS.
    # To fix: return default value or check if user_id in USERS.
    return USERS[user_id]

def get_item(index: int) -> str:
    # INTENTIONAL BUG: IndexError if index is out of bounds.
    # To fix: validate bounds before returning.
    return ITEMS[index]

class StandaloneRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - - {format % args}")

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
    port = int(os.environ.get("PORT", 8080))
    run_server(port=port)
