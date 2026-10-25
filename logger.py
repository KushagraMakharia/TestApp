import atexit
import json
import logging
import queue
import sys
import threading
import time
import urllib.request

from settings import APP_NAME, INGESTION_KEY, LOG_FILE, LOG_STREAM_URL


class HttpLogStreamHandler(logging.Handler):
    """Asynchronously streams log records in real time to the HTTP log ingestion endpoint."""

    def __init__(
        self,
        endpoint_url: str = LOG_STREAM_URL,
        ingestion_key: str = INGESTION_KEY,
        app_name: str = APP_NAME,
        batch_size: int = 50,
        flush_interval: float = 0.25,
        max_queue_size: int = 5000,
    ):
        super().__init__()
        self.endpoint_url = endpoint_url
        self.ingestion_key = ingestion_key
        self.app_name = app_name
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._queue: queue.Queue[str] = queue.Queue(maxsize=max_queue_size)
        self._stop_event = threading.Event()
        self._worker_thread: threading.Thread | None = None
        self._ensure_worker_running()

    def _ensure_worker_running(self):
        if self._worker_thread is None or not self._worker_thread.is_alive():
            self._stop_event.clear()
            self._worker_thread = threading.Thread(
                target=self._worker_loop, name="HttpLogStreamHandlerWorker", daemon=True
            )
            self._worker_thread.start()

    def emit(self, record: logging.LogRecord):
        # Ignore logs produced by our own background HTTP dispatcher thread to prevent recursion
        if threading.current_thread().name == "HttpLogStreamHandlerWorker":
            return
        try:
            self._ensure_worker_running()
            msg = self.format(record)
            if record.exc_info and not record.exc_text:
                record.exc_text = (
                    self.formatter.formatException(record.exc_info)
                    if self.formatter
                    else str(record.exc_info[1])
                )
            if record.exc_text and record.exc_text not in msg:
                msg = f"{msg}\n{record.exc_text}"
            self._queue.put_nowait(msg)
        except queue.Full:
            # Drop older logs when buffer is full to prevent blocking application
            pass
        except Exception:
            self.handleError(record)

    def _send_batch(self, batch: list[str]):
        if not batch or not self.endpoint_url:
            return
        payload = json.dumps({"app_name": self.app_name, "logs": batch}).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
        }
        if self.ingestion_key:
            headers["X-AutoCure-Ingestion-Key"] = self.ingestion_key

        req = urllib.request.Request(
            self.endpoint_url,
            data=payload,
            headers=headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=3.0) as resp:
                resp.read()
        except Exception:
            # Silently ignore network failures to avoid crashing or recursive logging
            pass

    def _worker_loop(self):
        while not self._stop_event.is_set():
            try:
                batch: list[str] = []
                deadline = time.time() + self.flush_interval
                while time.time() < deadline and len(batch) < self.batch_size:
                    try:
                        remaining = max(0.01, deadline - time.time())
                        item = self._queue.get(timeout=remaining)
                        batch.append(item)
                    except queue.Empty:
                        break

                if batch:
                    try:
                        self._send_batch(batch)
                    finally:
                        for _ in batch:
                            self._queue.task_done()
            except Exception:
                time.sleep(0.05)

    def flush(self):
        try:
            self._queue.join()
        except Exception:
            pass

    def close(self):
        self.flush()
        super().close()


class ApplicationLogger:
    """Configures and exposes the application's shared logger."""

    def __init__(self, name: str = "test_application"):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
        self._http_handler: HttpLogStreamHandler | None = None
        self._configure()

    def _configure(self):
        if self._logger.handlers:
            return

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

        file_handler = logging.FileHandler(str(LOG_FILE))
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self._logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(formatter)
        self._logger.addHandler(stream_handler)

        if LOG_STREAM_URL:
            self._http_handler = HttpLogStreamHandler(
                endpoint_url=LOG_STREAM_URL,
                ingestion_key=INGESTION_KEY,
                app_name=APP_NAME,
            )
            self._http_handler.setLevel(logging.DEBUG)
            self._http_handler.setFormatter(formatter)
            self._logger.addHandler(self._http_handler)

            # Also stream framework logs to AutoCure
            for extra_logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error", "fastapi"):
                extra_logger = logging.getLogger(extra_logger_name)
                extra_logger.addHandler(self._http_handler)

            atexit.register(self.flush)

    def flush(self):
        if self._http_handler:
            self._http_handler.flush()

    def debug(self, message, *args, **kwargs):
        self._logger.debug(message, *args, **kwargs)

    def info(self, message, *args, **kwargs):
        self._logger.info(message, *args, **kwargs)

    def warning(self, message, *args, **kwargs):
        self._logger.warning(message, *args, **kwargs)

    def error(self, message, *args, **kwargs):
        self._logger.error(message, *args, **kwargs)

    def exception(self, message, *args, **kwargs):
        self._logger.exception(message, *args, **kwargs)


logger = ApplicationLogger()