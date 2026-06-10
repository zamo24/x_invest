from fastapi import APIRouter

from app.api.routes import chat, health, ingest, library, model_settings, tokens, x_integration
from app.core.config import get_settings

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tokens.router, prefix="/v1", tags=["tokens"])
api_router.include_router(model_settings.router, prefix="/v1", tags=["model-settings"])
# Historical regression fixtures use this only in tests. Runtime X ingestion is exclusively /v1/sources/x.
if get_settings().app_env == "test":
    api_router.include_router(ingest.router, prefix="/v1", tags=["test-only-legacy-ingest"])
api_router.include_router(chat.router, prefix="/v1", tags=["chat"])
api_router.include_router(library.router, prefix="/v1", tags=["library"])
api_router.include_router(x_integration.router, prefix="/v1", tags=["x-integration"])
