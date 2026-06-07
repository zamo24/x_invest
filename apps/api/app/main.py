from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import api_router
from app.core.config import get_settings
from app.core.cors import parse_csv, resolve_cors_origin_regex, resolve_cors_origins, validate_cors_settings
from app.core.observability import RequestContextMiddleware, configure_logging, log_unhandled_exception
from app.core.rate_limit import RateLimitMiddleware

settings = get_settings()
configure_logging(settings.log_level)

app = FastAPI(title=settings.app_name)

validate_cors_settings(settings)

app.add_middleware(
    CORSMiddleware,
    allow_origins=resolve_cors_origins(settings),
    allow_origin_regex=resolve_cors_origin_regex(settings),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=parse_csv(settings.cors_allow_methods),
    allow_headers=parse_csv(settings.cors_allow_headers),
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
