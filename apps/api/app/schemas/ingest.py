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


class IngestArticlePayload(BaseModel):
    article_id: str | None = None
    url: str
    title: str
    author_handle: str | None = None
    author_name: str | None = None
    created_at: datetime | None = None
    text: str
    captured_at: datetime
    json_raw: dict[str, Any] | None = None


class IngestXRequest(BaseModel):
    capture_type: Literal["tweet", "thread", "article"]
    page_url: str
    root_tweet_id: str | None = None
    root_tweet_url: str | None = None
    tweets: list[IngestTweetPayload] = Field(default_factory=list)
    article: IngestArticlePayload | None = None
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
    source_kind: Literal["tweet", "article"] = "tweet"
    title: str | None = None
    folder_id: UUID | None
    folder_name: str | None = None
    content_status: str = "pending_verification"
    last_verified_at: datetime | None = None
    unavailable_reason: str | None = None


class ThreadCaptureSummary(BaseModel):
    id: UUID
    capture_version: int
    captured_at: datetime
    is_partial: bool
    partial_reason: str | None = None
    item_count: int


class ThreadCaptureItem(BaseModel):
    id: UUID | None = None
    item_order: int
    tweet_id: str
    url: str
    author_handle: str
    author_name: str | None = None
    created_at: datetime | None = None
    captured_at: datetime
    text: str
    source_kind: Literal["tweet"] = "tweet"
    title: None = None
    folder_id: None = None
    folder_name: None = None


class ThreadDetailResponse(BaseModel):
    thread: LibraryThreadListItem
    selected_capture: ThreadCaptureSummary
    captures: list[ThreadCaptureSummary]
    items: list[ThreadCaptureItem]
