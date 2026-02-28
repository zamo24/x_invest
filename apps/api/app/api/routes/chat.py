from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_any_authenticated_user
from app.db.models import User
from app.db.session import get_db
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.embeddings import embed_text
from app.services.rag import build_answer, retrieve_chunks

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> ChatResponse:
    thread_id = None
    if payload.scope == "thread":
        if not payload.thread_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="thread_id is required when scope='thread'",
            )
        try:
            from uuid import UUID

            thread_id = UUID(payload.thread_id)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid thread_id") from exc

    query_vec = embed_text(payload.message)
    retrieved = retrieve_chunks(
        db,
        user_id=user.id,
        query_vector=query_vec,
        scope=payload.scope,
        thread_id=thread_id,
        top_k=payload.top_k,
        filters=payload.filters,
    )

    bundle = build_answer(payload.message, retrieved)
    return ChatResponse(answer_text=bundle.answer_text, cited_sources=bundle.cited_sources)
