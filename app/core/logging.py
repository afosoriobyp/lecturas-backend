from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.log_config import ContextJSONFormatter, endpoint_var, setup_json_logging, trace_id_var

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = (time.perf_counter() - start) * 1000

        access_logger = logging.getLogger("access")
        extra = {
            "duration_ms": round(elapsed, 2),
            "request_id": trace_id_var.get() or None,
            "endpoint": endpoint_var.get() or request.url.path,
        }
        access_logger.info(
            "%s %s -> %d (%.1fms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
            extra=extra,
        )
        return response


def setup_logging() -> None:
    setup_json_logging()
    logger.info("Logging configurado con formato JSON y rotación diaria")


def register_middleware(app: FastAPI) -> None:
    app.add_middleware(RequestLoggingMiddleware)
