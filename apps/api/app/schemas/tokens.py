from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TokenCreateRequest(BaseModel):
    name: str


class TokenCreateResponse(BaseModel):
    id: UUID
    name: str
    token: str
    token_fingerprint: str
    created_at: datetime


class TokenListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    token_fingerprint: str
    created_at: datetime
    last_used_at: datetime | None
    revoked_at: datetime | None


class TokenRevokeResponse(BaseModel):
    id: UUID
    revoked_at: datetime
