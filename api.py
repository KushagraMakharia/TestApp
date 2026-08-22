import json
import traceback

import httpx
from fastapi import FastAPI, Header, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse

from domain import divide, get_item, get_user
from logger import logger
from settings import ERROR_WEBHOOK_URL, LOG_FILE


async def send_error_to_webhook(error_type: str, error_message: str, error_traceback: str):
    try:
        async with httpx.AsyncClient() as client:
            await client.post(
                ERROR_WEBHOOK_URL,
                json={
                    "error_type": error_type,
                    "error_message": error_message,
                    "traceback": error_traceback,
                },
                timeout=5.0,
            )
    except Exception as exc:
        logger.error(f"Failed to send error to webhook: {exc}")


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


app = FastAPI(title="Standalone Target Test Application")


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    error_type = type(exc).__name__
    error_message = str(exc)
    error_traceback = traceback.format_exc()
    logger.error(f"Exception caught: {error_type} - {error_message}\n{error_traceback}")
    await send_error_to_webhook(error_type, error_message, error_traceback)
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_type": error_type,
            "error_message": error_message,
        },
    )


@app.get("/health")
async def health() -> dict:
    return {"status": "healthy"}


@app.get("/calculate")
async def calculate(a: int = Query(...), b: int = Query(...)) -> dict:
    return {"result": divide(a, b)}


@app.get("/users")
async def users(user_id: str = Query(..., alias="id")) -> dict:
    return {"user": get_user(user_id)}


@app.get("/items")
async def items(index: int = Query(...)) -> dict:
    return {"item": get_item(index)}


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
    payload = await request.json()
    error_type = payload.get("error_type")
    error_message = payload.get("error_message")
    error_traceback = payload.get("traceback")
    logger.error(f"Webhook received error: {error_type} - {error_message}")
    logger.error(f"Traceback:\n{error_traceback}")
    return {"status": "received", "error_type": error_type}
