from datetime import datetime, timezone

from fastapi import APIRouter, Request

from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health(request: Request) -> dict[str, str | bool | None]:
    return {
        "ok": True,
        "env": settings.app_env,
        "version": settings.app_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(request.state, "request_id", None),
    }
