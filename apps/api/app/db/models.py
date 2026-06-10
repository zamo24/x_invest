from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

EMBEDDING_DIM = 256


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_user_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    api_tokens: Mapped[list[ApiToken]] = relationship(back_populates="user", cascade="all, delete-orphan")
    folders: Mapped[list[XFolder]] = relationship(back_populates="user", cascade="all, delete-orphan")
    model_settings: Mapped[UserModelSettings | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )
    chat_threads: Mapped[list[ChatThread]] = relationship(back_populates="user", cascade="all, delete-orphan")
    x_integration: Mapped[XIntegration | None] = relationship(
        back_populates="user", cascade="all, delete-orphan", uselist=False
    )


class ApiToken(Base):
    __tablename__ = "api_tokens"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    token_fingerprint: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="api_tokens")


class UserModelSettings(Base):
    __tablename__ = "user_model_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    inference_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="hosted", server_default="hosted")
    preferred_provider: Mapped[str] = mapped_column(String(50), nullable=False, default="openai", server_default="openai")
    preferred_model: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reasoning_effort: Mapped[str] = mapped_column(String(20), nullable=False, default="medium", server_default="medium")
    byo_openai_api_key_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    byo_openai_api_key_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    byo_openai_api_key_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="model_settings")


class XItem(Base):
    __tablename__ = "x_items"
    __table_args__ = (UniqueConstraint("user_id", "tweet_id", name="uq_x_items_user_tweet"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_folders.id", ondelete="SET NULL"), index=True, nullable=True
    )
    tweet_id: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    author_handle: Mapped[str] = mapped_column(String(100), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    quoted_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    json_raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    external_source: Mapped[str] = mapped_column(String(30), nullable=False, default="x", server_default="x")
    external_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    content_status: Mapped[str] = mapped_column(
        String(30), nullable=False, default="pending_verification", server_default="pending_verification", index=True
    )
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_content_change_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    unavailable_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class XIntegration(Base):
    __tablename__ = "x_integrations"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    x_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    x_username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    access_token_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token_encrypted: Mapped[str | None] = mapped_column(Text, nullable=True)
    access_token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    granted_scopes: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="connected", server_default="connected")
    bookmark_sync_cursor: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_bookmark_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_bookmark_sync_result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="x_integration")


class XOAuthState(Base):
    __tablename__ = "x_oauth_states"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    state_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    pkce_verifier_encrypted: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class XApiUsage(Base):
    __tablename__ = "x_api_usage"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    operation: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    requested_post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    returned_post_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class XBookmarkFolderMapping(Base):
    __tablename__ = "x_bookmark_folder_mappings"
    __table_args__ = (UniqueConstraint("user_id", "x_folder_id", name="uq_x_bookmark_folder_mapping"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    x_folder_id: Mapped[str] = mapped_column(String(100), nullable=False)
    x_folder_name: Mapped[str] = mapped_column(String(200), nullable=False)
    local_folder_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_folders.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class XThread(Base):
    __tablename__ = "x_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    folder_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_folders.id", ondelete="SET NULL"), index=True, nullable=True
    )
    root_tweet_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    root_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(280), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    capture_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    is_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    partial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class XThreadItem(Base):
    __tablename__ = "x_thread_items"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_threads.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_items.id", ondelete="CASCADE"), primary_key=True
    )


class XThreadCapture(Base):
    __tablename__ = "x_thread_captures"
    __table_args__ = (UniqueConstraint("thread_id", "capture_version", name="uq_x_thread_captures_thread_version"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_threads.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    capture_version: Mapped[int] = mapped_column(Integer, nullable=False)
    root_tweet_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    root_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    title: Mapped[str] = mapped_column(String(280), nullable=False)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    is_partial: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    partial_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    macro_chunk_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class XThreadCaptureItem(Base):
    __tablename__ = "x_thread_capture_items"

    capture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_thread_captures.id", ondelete="CASCADE"), primary_key=True
    )
    item_order: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("x_items.id", ondelete="SET NULL"), index=True, nullable=True
    )
    tweet_id: Mapped[str] = mapped_column(String(64), nullable=False)
    url: Mapped[str] = mapped_column(String(500), nullable=False)
    author_handle: Mapped[str] = mapped_column(String(100), nullable=False)
    author_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    quoted_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    json_raw: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)


class XFolder(Base):
    __tablename__ = "x_folders"
    __table_args__ = (UniqueConstraint("user_id", "name", name="uq_x_folders_user_name"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    user: Mapped[User] = relationship(back_populates="folders")


class Chunk(Base):
    __tablename__ = "chunks"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    source_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    chunk_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class ChatThread(Base):
    __tablename__ = "chat_threads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="chat_threads")
    messages: Mapped[list[ChatMessage]] = relationship(back_populates="thread", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    cited_sources_json: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB, nullable=True)
    provider_used: Mapped[str | None] = mapped_column(String(50), nullable=True)
    model_used: Mapped[str | None] = mapped_column(String(120), nullable=True)
    inference_mode_used: Mapped[str | None] = mapped_column(String(20), nullable=True)
    reasoning_effort_used: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    thread: Mapped[ChatThread] = relationship(back_populates="messages")
