from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_any_authenticated_user
from app.db.models import ChatMessage, ChatThread, User
from app.db.session import get_db
from app.schemas.chat import (
    ChatMessageItem,
    ChatRequest,
    ChatResponse,
    ChatThreadDetail,
    ChatThreadListItem,
    ChatThreadUpdateRequest,
    CitedSource,
)
from app.services.embeddings import embed_text
from app.services.model_settings import ModelSettingsError, resolve_chat_execution
from app.services.openai_client import OpenAIServiceError
from app.services.rag import build_answer, retrieve_chunks

router = APIRouter()


def _build_thread_title(message: str) -> str:
    cleaned = " ".join((message or "").split()).strip()
    if not cleaned:
        return "New Chat"
    return cleaned[:120]


def _normalize_chat_thread_title(title: str) -> str:
    cleaned = " ".join((title or "").split()).strip()
    if not cleaned:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Thread title cannot be empty.",
        )
    return cleaned[:200]


def _load_chat_thread_or_404(*, db: Session, user_id: UUID, chat_thread_id: UUID) -> ChatThread:
    thread = db.execute(
        select(ChatThread).where(ChatThread.id == chat_thread_id, ChatThread.user_id == user_id)
    ).scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chat thread not found")
    return thread


def _recent_history(*, db: Session, thread_id: UUID, max_messages: int = 8) -> list[tuple[str, str]]:
    rows = db.execute(
        select(ChatMessage.role, ChatMessage.message_text)
        .where(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(max_messages)
    ).all()
    rows.reverse()
    return [(role, text) for role, text in rows]


def _thread_list_item(*, db: Session, thread: ChatThread) -> ChatThreadListItem:
    counts = db.execute(
        select(
            func.count(ChatMessage.id).label("message_count"),
            func.max(ChatMessage.created_at).label("last_message_at"),
        ).where(ChatMessage.thread_id == thread.id)
    ).one()
    return ChatThreadListItem(
        id=thread.id,
        title=thread.title,
        created_at=thread.created_at,
        updated_at=thread.updated_at,
        last_message_at=counts.last_message_at,
        message_count=int(counts.message_count or 0),
    )


def _parse_thread_scope_id(payload: ChatRequest) -> UUID | None:
    if payload.scope != "thread":
        return None
    if not payload.thread_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="thread_id is required when scope='thread'",
        )
    try:
        return UUID(payload.thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid thread_id") from exc


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    try:
        chat_execution = resolve_chat_execution(
            db=db,
            user=user,
            requested_provider=payload.provider,
            requested_model=payload.model,
        )
    except ModelSettingsError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    library_thread_id = _parse_thread_scope_id(payload)

    if payload.chat_thread_id:
        chat_thread = _load_chat_thread_or_404(db=db, user_id=user.id, chat_thread_id=payload.chat_thread_id)
    else:
        chat_thread = ChatThread(user_id=user.id, title=_build_thread_title(payload.message))
        db.add(chat_thread)
        db.flush()

    history = _recent_history(db=db, thread_id=chat_thread.id, max_messages=8)

    try:
        query_vec = embed_text(payload.message)
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    retrieved = retrieve_chunks(
        db,
        user_id=user.id,
        query_text=payload.message,
        query_vector=query_vec,
        scope=payload.scope,
        thread_id=library_thread_id,
        top_k=payload.top_k,
        filters=payload.filters,
    )

    try:
        bundle = build_answer(
            payload.message,
            retrieved,
            chat_model=chat_execution.model,
            reasoning_effort=chat_execution.reasoning_effort,
            api_key=chat_execution.api_key,
            history=history,
        )
    except OpenAIServiceError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    now = datetime.now(timezone.utc)
    user_message = ChatMessage(
        thread_id=chat_thread.id,
        user_id=user.id,
        role="user",
        message_text=payload.message.strip(),
    )
    assistant_message = ChatMessage(
        thread_id=chat_thread.id,
        user_id=user.id,
        role="assistant",
        message_text=bundle.answer_text,
        cited_sources_json=[source.model_dump(mode="json") for source in bundle.cited_sources],
        provider_used=chat_execution.provider,
        model_used=chat_execution.model,
        inference_mode_used=chat_execution.inference_mode,
        reasoning_effort_used=chat_execution.reasoning_effort,
    )
    chat_thread.updated_at = now
    db.add(user_message)
    db.add(assistant_message)
    db.add(chat_thread)
    db.commit()

    return ChatResponse(
        chat_thread_id=chat_thread.id,
        answer_text=bundle.answer_text,
        cited_sources=bundle.cited_sources,
        provider_used=chat_execution.provider,
        model_used=chat_execution.model,
        inference_mode_used=chat_execution.inference_mode,
        reasoning_effort_used=chat_execution.reasoning_effort,
    )


@router.get("/chat/threads", response_model=list[ChatThreadListItem])
def list_chat_threads(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> list[ChatThreadListItem]:
    threads = db.execute(
        select(ChatThread)
        .where(ChatThread.user_id == user.id)
        .order_by(ChatThread.updated_at.desc(), ChatThread.id.desc())
        .offset(offset)
        .limit(limit)
    ).scalars().all()
    return [_thread_list_item(db=db, thread=thread) for thread in threads]


@router.get("/chat/threads/{chat_thread_id}", response_model=ChatThreadDetail)
def get_chat_thread(
    chat_thread_id: UUID,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> ChatThreadDetail:
    thread = _load_chat_thread_or_404(db=db, user_id=user.id, chat_thread_id=chat_thread_id)
    messages = db.execute(
        select(ChatMessage).where(ChatMessage.thread_id == thread.id).order_by(ChatMessage.created_at.asc())
    ).scalars().all()

    response_messages: list[ChatMessageItem] = []
    for msg in messages:
        raw_sources = msg.cited_sources_json if isinstance(msg.cited_sources_json, list) else []
        parsed_sources: list[CitedSource] = []
        for raw in raw_sources:
            if isinstance(raw, dict):
                try:
                    parsed_sources.append(CitedSource.model_validate(raw))
                except Exception:
                    continue

        role = msg.role if msg.role in {"user", "assistant"} else "assistant"
        response_messages.append(
            ChatMessageItem(
                id=msg.id,
                role=role,  # type: ignore[arg-type]
                message_text=msg.message_text,
                cited_sources=parsed_sources,
                provider_used=msg.provider_used,  # type: ignore[arg-type]
                model_used=msg.model_used,
                inference_mode_used=msg.inference_mode_used,  # type: ignore[arg-type]
                reasoning_effort_used=msg.reasoning_effort_used,  # type: ignore[arg-type]
                created_at=msg.created_at,
            )
        )

    return ChatThreadDetail(
        thread=_thread_list_item(db=db, thread=thread),
        messages=response_messages,
    )


@router.patch("/chat/threads/{chat_thread_id}", response_model=ChatThreadListItem)
def update_chat_thread(
    chat_thread_id: UUID,
    payload: ChatThreadUpdateRequest,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> ChatThreadListItem:
    thread = _load_chat_thread_or_404(db=db, user_id=user.id, chat_thread_id=chat_thread_id)
    thread.title = _normalize_chat_thread_title(payload.title)
    thread.updated_at = datetime.now(timezone.utc)
    db.add(thread)
    db.commit()
    db.refresh(thread)
    return _thread_list_item(db=db, thread=thread)


@router.delete("/chat/threads/{chat_thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_chat_thread(
    chat_thread_id: UUID,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> Response:
    thread = _load_chat_thread_or_404(db=db, user_id=user.id, chat_thread_id=chat_thread_id)
    db.delete(thread)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
