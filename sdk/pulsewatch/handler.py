import logging
from typing import Optional
from pulsewatch.client import PulseWatchClient

STANDARD_LOG_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message"
}


class PulseWatchHandler(logging.Handler):
    """
    Standard Python logging.Handler that forwards all application log records
    to a PulseWatchClient instance with zero blocking overhead.
    """

    def __init__(self, client: PulseWatchClient, level: int = logging.NOTSET):
        super().__init__(level=level)
        self.client = client

    def emit(self, record: logging.LogRecord):
        try:
            msg = self.format(record)
            metadata = {}

            # Capture extra contextual attributes attached to the record
            for k, v in record.__dict__.items():
                if k not in STANDARD_LOG_ATTRS and not k.startswith("_"):
                    try:
                        # Ensure JSON serializable
                        str(v)
                        metadata[k] = v
                    except Exception:
                        pass

            # Include exception stack traces if present
            if record.exc_info:
                metadata["exception"] = self.formatException(record.exc_info)

            # Enqueue log
            self.client.send_log(
                message=msg,
                level=record.levelname,
                metadata=metadata,
            )
        except Exception:
            self.handleError(record)
