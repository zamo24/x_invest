from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class FolderCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FolderResponse(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    item_count: int
    thread_count: int


class FolderAssignRequest(BaseModel):
    folder_id: UUID | None = None


class FolderAssignmentResponse(BaseModel):
    id: UUID
    folder_id: UUID | None = None
    folder_name: str | None = None
