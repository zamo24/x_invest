from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class QuotedTweetPayload(BaseModel):
    tweet_id: str | None = None
    url: str | None = None
    text: str
    author_handle: str | None = None
    author_name: str | None = None
    created_at: datetime | None = None


class IngestTweetPayload(BaseModel):
    tweet_id: str | None = None
    url: str
    author_handle: str
    author_name: str | None = None
    created_at: datetime | None = None
    text: str
    quoted: QuotedTweetPayload | None = None
    captured_at: datetime
    json_raw: dict[str, Any] | None = None


class IngestXRequest(BaseModel):
    capture_type: Literal["tweet", "thread"]
    page_url: str
    root_tweet_id: str | None = None
    root_tweet_url: str | None = None
    tweets: list[IngestTweetPayload] = Field(default_factory=list)
    captured_count: int
    folder_id: UUID | None = None
    is_partial: bool = False
    partial_reason: str | None = None


class IngestXResponse(BaseModel):
    thread_id: UUID | None = None
    thread_version: int | None = None
    item_ids: list[UUID]
    stored_count: int
    is_partial: bool


class LibraryThreadListItem(BaseModel):
    id: UUID
    root_tweet_id: str | None
    root_url: str | None
    title: str
    captured_at: datetime
    capture_version: int
    is_partial: bool
    item_count: int
    author_handles: list[str] = Field(default_factory=list)
    folder_id: UUID | None = None
    folder_name: str | None = None


class LibraryItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tweet_id: str
    url: str
    author_handle: str
    author_name: str | None
    created_at: datetime | None
    captured_at: datetime
    text: str
    folder_id: UUID | None
    folder_name: str | None = None


class ThreadDetailResponse(BaseModel):
    thread: LibraryThreadListItem
    items: list[LibraryItem]
