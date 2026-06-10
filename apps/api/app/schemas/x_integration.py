from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class XStatusResponse(BaseModel):
    connected: bool
    status: str
    x_user_id: str | None = None
    x_username: str | None = None
    granted_scopes: list[str] = []
    connected_at: datetime | None = None
    last_bookmark_sync_at: datetime | None = None
    last_bookmark_sync_result: dict | None = None
    monthly_post_reads: int = 0
    monthly_post_read_budget: int = 0


class XAuthorizeResponse(BaseModel):
    authorization_url: str
    expires_at: datetime


class XSourceRequest(BaseModel):
    url: str
    folder_id: UUID | None = None
    mode: Literal["post", "author_thread"] = "post"


class XSourceResponse(BaseModel):
    item_ids: list[UUID]
    thread_id: UUID | None = None
    thread_version: int | None = None
    created: int = 0
    updated: int = 0
    is_partial: bool = False
    partial_reason: str | None = None


class XBookmarkSyncResponse(BaseModel):
    fetched: int = 0
    created: int = 0
    updated: int = 0
    unavailable: int = 0
    failed: int = 0
    folders_mapped: int = 0
    partial: bool = False
