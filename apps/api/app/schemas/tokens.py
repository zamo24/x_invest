from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TokenCreateRequest(BaseModel):
    name: str
    expires_in_days: int | None = Field(default=None, ge=1)

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            return "Default token"
        if len(cleaned) > 120:
            raise ValueError("name must be 120 characters or fewer")
        return cleaned


class TokenCreateResponse(BaseModel):
    id: UUID
    name: str
    token: str
    token_fingerprint: str
    created_at: datetime
    expires_at: datetime | None


class TokenListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    token_fingerprint: str
    created_at: datetime
    last_used_at: datetime | None
    expires_at: datetime | None
    revoked_at: datetime | None


class TokenRevokeResponse(BaseModel):
    id: UUID
    revoked_at: datetime
