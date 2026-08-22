import json
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CONFIG_FILE = BASE_DIR / "config.json"
LOG_FILE = BASE_DIR / "app.log"

with CONFIG_FILE.open("r", encoding="utf-8") as config_handle:
	CONFIG = json.load(config_handle)

ERROR_WEBHOOK_URL = CONFIG["error_webhook_url"]
