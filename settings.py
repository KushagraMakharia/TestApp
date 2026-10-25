import json
import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = BASE_DIR / "app.log"


def _resolve_docker_host(url: str) -> str:
    """If running inside a Docker container, rewrite localhost/127.0.0.1 to host.docker.internal."""
    if not url:
        return url
    if ":8000:8000" in url:
        url = url.replace(":8000:8000", ":8000")
    is_docker = Path("/.dockerenv").exists() or os.environ.get("DOCKER_CONTAINER") == "true"
    if is_docker:
        url = url.replace("://localhost:", "://host.docker.internal:")
        url = url.replace("://127.0.0.1:", "://host.docker.internal:")
    return url


CONFIG = {}
if CONFIG_FILE.exists():
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as config_handle:
            CONFIG = json.load(config_handle)
    except Exception:
        CONFIG = {}

ERROR_WEBHOOK_URL = _resolve_docker_host(
    os.environ.get(
        "ERROR_WEBHOOK_URL",
        CONFIG.get("error_webhook_url", "http://localhost:8000/api/v1/projects/testapp/webhook"),
    )
)
LOG_STREAM_URL = _resolve_docker_host(
    os.environ.get(
        "LOG_STREAM_URL",
        CONFIG.get("log_stream_url", "http://localhost:8000/api/v1/projects/testapp/logs"),
    )
)
INGESTION_KEY = os.environ.get(
    "INGESTION_KEY",
    CONFIG.get("ingestion_key", "qd8Ov-JX3ZBAyOs_qhxqdFAm6enAG-2ty6UGer4AHOY"),
)
APP_NAME = os.environ.get(
    "APP_NAME",
    CONFIG.get("app_name", "testapp"),
)
