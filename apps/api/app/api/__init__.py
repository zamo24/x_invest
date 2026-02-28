from fastapi import APIRouter

from app.api.routes import chat, health, ingest, library, tokens

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(tokens.router, prefix="/v1", tags=["tokens"])
api_router.include_router(ingest.router, prefix="/v1", tags=["ingest"])
api_router.include_router(chat.router, prefix="/v1", tags=["chat"])
api_router.include_router(library.router, prefix="/v1", tags=["library"])
