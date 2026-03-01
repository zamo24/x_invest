from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class DateRangeFilter(BaseModel):
    start: date | None = None
    end: date | None = None


class ChatFilters(BaseModel):
    author_handle: str | None = None
    date_range: DateRangeFilter | None = None
    folder_id: UUID | None = None


class ChatRequest(BaseModel):
    message: str
    scope: Literal["all", "thread"] = "all"
    thread_id: str | None = None
    filters: ChatFilters | None = None
    top_k: int = Field(default=8, ge=1, le=25)


class CitedSource(BaseModel):
    tweet_url: str
    tweet_id: str | None = None
    author_handle: str | None = None
    created_at: datetime | None = None
    snippet: str


class ChatResponse(BaseModel):
    answer_text: str
    cited_sources: list[CitedSource]
