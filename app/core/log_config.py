from __future__ import annotations

import json
import logging
import os
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import TimedRotatingFileHandler
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

trace_id_var: ContextVar[str] = ContextVar("trace_id", default="")
user_id_var: ContextVar[str] = ContextVar("user_id", default="")
endpoint_var: ContextVar[str] = ContextVar("endpoint", default="")
error_code_var: ContextVar[str] = ContextVar("error_code", default="")


class ContextJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": trace_id_var.get() or None,
            "user_id": user_id_var.get() or None,
            "endpoint": endpoint_var.get() or None,
            "error_code": error_code_var.get() or None,
        }
        if record.exc_info and record.exc_info[0]:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, "duration_ms"):
            log_entry["duration_ms"] = record.duration_ms
        return json.dumps(log_entry, default=str, ensure_ascii=False)


class TraceIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        from uuid import uuid4

        trace_id = str(uuid4())
        request.state.trace_id = trace_id
        trace_id_var.set(trace_id)
        endpoint_var.set(request.url.path)

        response = await call_next(request)
        response.headers["X-Trace-Id"] = trace_id
        return response


def setup_json_logging() -> None:
    from app.core.config import settings

    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler()
    if settings.LOG_FORMAT == "json":
        console_handler.setFormatter(ContextJSONFormatter())
    else:
        console_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
    root_logger.addHandler(console_handler)

    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "app.log"),
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8",
    )
    file_handler.setFormatter(ContextJSONFormatter())
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    error_file_handler = TimedRotatingFileHandler(
        os.path.join(log_dir, "error.log"),
        when="midnight",
        interval=1,
        backupCount=90,
        encoding="utf-8",
    )
    error_file_handler.setFormatter(ContextJSONFormatter())
    error_file_handler.setLevel(logging.ERROR)
    root_logger.addHandler(error_file_handler)

    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
