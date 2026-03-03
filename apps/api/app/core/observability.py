from __future__ import annotations

import contextvars
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

_request_id_ctx_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)

LOGGER = logging.getLogger("app.access")
ERROR_LOGGER = logging.getLogger("app.error")


def get_request_id() -> str | None:
    return _request_id_ctx_var.get()


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def _json_log(payload: dict[str, Any]) -> str:
    return json.dumps(payload, separators=(",", ":"), default=str)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request_id = request_id.strip()[:128]
        token = _request_id_ctx_var.set(request_id)
        request.state.request_id = request_id

        start = time.perf_counter()
        response: Response | None = None

        try:
            response = await call_next(request)
            return response
        finally:
            duration_ms = round((time.perf_counter() - start) * 1000.0, 2)
            status_code = response.status_code if response is not None else 500
            user_id = getattr(request.state, "auth_user_id", None)
            LOGGER.info(
                _json_log(
                    {
                        "event": "request_complete",
                        "ts": datetime.now(timezone.utc).isoformat(),
                        "request_id": request_id,
                        "method": request.method,
                        "path": request.url.path,
                        "status_code": status_code,
                        "duration_ms": duration_ms,
                        "user_id": user_id,
                        "client_ip": request.client.host if request.client else None,
                    }
                )
            )
            if response is not None:
                response.headers["x-request-id"] = request_id
            _request_id_ctx_var.reset(token)


def log_unhandled_exception(request: Request, exc: Exception) -> None:
    ERROR_LOGGER.exception(
        _json_log(
            {
                "event": "unhandled_exception",
                "request_id": getattr(request.state, "request_id", get_request_id()),
                "path": request.url.path,
                "method": request.method,
                "error_type": type(exc).__name__,
            }
        )
    )
