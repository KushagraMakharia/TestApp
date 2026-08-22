import logging
import sys

from settings import LOG_FILE


class ApplicationLogger:
    """Configures and exposes the application's shared logger."""

    def __init__(self, name: str = "test_application"):
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)
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