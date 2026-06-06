from __future__ import annotations

from dataclasses import dataclass
import hashlib
import time
from collections.abc import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import Settings, get_settings


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    reset_after_seconds: int


@dataclass
class _Bucket:
    count: int
    reset_at: float


class FixedWindowRateLimiter:
    def __init__(self) -> None:
        self._buckets: dict[str, _Bucket] = {}

    def check(self, key: str, *, limit: int, window_seconds: int, now: float | None = None) -> RateLimitDecision:
        checked_at = time.time() if now is None else now
        window = max(1, window_seconds)
        capped_limit = max(1, limit)
        bucket = self._buckets.get(key)

        if bucket is None or bucket.reset_at <= checked_at:
            bucket = _Bucket(count=0, reset_at=checked_at + window)
            self._buckets[key] = bucket

        reset_after = max(1, int(bucket.reset_at - checked_at))
        if bucket.count >= capped_limit:
            return RateLimitDecision(allowed=False, remaining=0, reset_after_seconds=reset_after)

        bucket.count += 1
        remaining = max(0, capped_limit - bucket.count)
        return RateLimitDecision(allowed=True, remaining=remaining, reset_after_seconds=reset_after)


def _route_group(path: str) -> str | None:
    if path == "/v1/chat" or path.startswith("/v1/chat/"):
        return "chat"
    if path == "/v1/ingest/x":
        return "ingest"
    if path == "/v1/tokens" or path.startswith("/v1/tokens/"):
        return "tokens"
    return None


def _limit_for_group(settings: Settings, group: str) -> int:
    if group == "chat":
        return settings.rate_limit_chat_requests
    if group == "ingest":
        return settings.rate_limit_ingest_requests
    if group == "tokens":
        return settings.rate_limit_token_requests
    return settings.rate_limit_chat_requests


def _request_subject(request: Request) -> str:
    auth_header = request.headers.get("authorization")
    if auth_header:
        digest = hashlib.sha256(auth_header.encode("utf-8")).hexdigest()[:32]
        return f"auth:{digest}"

    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        settings_factory: Callable[[], Settings] = get_settings,
        limiter: FixedWindowRateLimiter | None = None,
    ) -> None:
        super().__init__(app)
        self._settings_factory = settings_factory
        self._limiter = limiter or FixedWindowRateLimiter()

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        settings = self._settings_factory()
        if not settings.rate_limit_enabled:
            return await call_next(request)

        group = _route_group(request.url.path)
        if group is None:
            return await call_next(request)

        limit = _limit_for_group(settings, group)
        key = f"{group}:{_request_subject(request)}"
        decision = self._limiter.check(
            key,
            limit=limit,
            window_seconds=settings.rate_limit_window_seconds,
        )
        if decision.allowed:
            response = await call_next(request)
            response.headers.setdefault("x-ratelimit-limit", str(limit))
            response.headers.setdefault("x-ratelimit-remaining", str(decision.remaining))
            response.headers.setdefault("x-ratelimit-reset", str(decision.reset_after_seconds))
            return response

        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=429,
            content={
                "detail": "Rate limit exceeded.",
                "request_id": request_id,
            },
            headers={
                "retry-after": str(decision.reset_after_seconds),
                "x-ratelimit-limit": str(limit),
                "x-ratelimit-remaining": "0",
                "x-ratelimit-reset": str(decision.reset_after_seconds),
            },
        )
