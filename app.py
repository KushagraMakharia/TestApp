import os

import uvicorn

from api import app, global_exception_handler, send_error_to_webhook
from domain import divide, get_item, get_user
from logger import logger
from standalone_server import StandaloneRequestHandler
from settings import LOG_FILE


def run_server(port=8080):
    from http.server import HTTPServer

    httpd = HTTPServer(("", port), StandaloneRequestHandler)
    logger.info(f"Starting test application server on port {port}...")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping test application server...")
        httpd.server_close()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    logger.info(f"Starting test application server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)

