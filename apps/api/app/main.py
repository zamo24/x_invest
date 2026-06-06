from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.observability import RequestContextMiddleware, configure_logging, log_unhandled_exception
from app.core.rate_limit import RateLimitMiddleware

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _validate_cors_settings() -> None:
    allow_origins = _parse_csv(settings.cors_allow_origins)
    if settings.cors_allow_credentials and "*" in allow_origins:
        raise RuntimeError("Invalid CORS config: wildcard origin is not allowed when credentials are enabled.")
    if not allow_origins and not settings.cors_allow_origin_regex:
        raise RuntimeError("Invalid CORS config: set at least one CORS origin or origin regex.")


_validate_cors_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=_parse_csv(settings.cors_allow_origins),
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=_parse_csv(settings.cors_allow_methods),
    allow_headers=_parse_csv(settings.cors_allow_headers),
)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(RequestContextMiddleware)


@app.middleware("http")
async def security_headers_middleware(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("x-content-type-options", "nosniff")
    response.headers.setdefault("x-frame-options", "DENY")
    response.headers.setdefault("referrer-policy", "strict-origin-when-cross-origin")
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    log_unhandled_exception(request, exc)
    request_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "request_id": request_id},
    )

app.include_router(api_router)
