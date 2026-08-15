import logging
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

LOG_DIR = Path(__file__).resolve().parent
LOG_FILE = LOG_DIR / "app.log"

logger = logging.getLogger("test_application")
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler(str(LOG_FILE))
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
logger.addHandler(stream_handler)

USERS = {"1": "Alice", "2": "Bob"}
ITEMS = ["apple", "banana", "cherry"]


def divide(a: int, b: int) -> float:
    if b == 0:
        return 0.0
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


app = FastAPI(title="Standalone Target Test Application")


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.get("/calculate")
async def calculate(a: int = Query(...), b: int = Query(...)) -> dict:
    if b == 0:
        raise HTTPException(status_code=400, detail="Division by zero is not supported.")
    return {"result": divide(a, b)}


@app.get("/users")
async def users(user_id: str = Query(..., alias="id")) -> dict:
    user = get_user(user_id)
    if user == "Unknown User":
        raise HTTPException(status_code=404, detail="User not found.")
    return {"user": user}


@app.get("/items")
async def items(index: int = Query(...)) -> dict:
    item = get_item(index)
    if item == "Unknown Item":
        raise HTTPException(status_code=404, detail="Item not found.")
    return {"item": item}


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting test application server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port)
