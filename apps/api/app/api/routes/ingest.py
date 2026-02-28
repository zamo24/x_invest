from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, get_auth_user
from app.db.models import Chunk, XItem, XThread, XThreadItem
from app.db.session import get_db
from app.schemas.ingest import IngestXRequest, IngestXResponse
from app.services.embeddings import embed_text
from app.services.ingest import (
    build_item_chunk_text,
    build_thread_macro_chunk_text,
    build_thread_title,
    coalesce_capture_time,
    normalize_tweet_id,
    stable_item_hash,
)

router = APIRouter()


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


@router.post("/ingest/x", response_model=IngestXResponse)
def ingest_x(
    payload: IngestXRequest,
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> IngestXResponse:
    user = auth_user.user

    seen_tweet_ids: set[str] = set()
    item_ids = []
    items_for_request: list[XItem] = []
    stored_count = 0

    for tw in payload.tweets:
        tweet_id = normalize_tweet_id(tw.tweet_id, tw.url, tw.text)
        if tweet_id in seen_tweet_ids:
            continue
        seen_tweet_ids.add(tweet_id)

        item = db.execute(
            select(XItem).where(XItem.user_id == user.id, XItem.tweet_id == tweet_id)
        ).scalar_one_or_none()

        if item is None:
            item = XItem(
                user_id=user.id,
                tweet_id=tweet_id,
                url=tw.url,
                author_handle=tw.author_handle,
                author_name=tw.author_name,
                created_at=_ensure_utc(tw.created_at),
                captured_at=_ensure_utc(coalesce_capture_time(tw.captured_at)) or datetime.now(timezone.utc),
                text=tw.text,
                quoted_json=tw.quoted.model_dump() if tw.quoted else None,
                json_raw=tw.json_raw,
                hash=stable_item_hash(user.id, tweet_id, tw.url, tw.text),
            )
            db.add(item)
            db.flush()
            stored_count += 1

        item_ids.append(item.id)
        items_for_request.append(item)

        existing_chunk = db.execute(
            select(Chunk).where(
                Chunk.user_id == user.id,
                Chunk.source_type == "x_item",
                Chunk.source_id == item.id,
                Chunk.chunk_order == 0,
            )
        ).scalar_one_or_none()

        if existing_chunk is None:
            item_text = build_item_chunk_text(item)
            item_chunk = Chunk(
                user_id=user.id,
                source_type="x_item",
                source_id=item.id,
                chunk_text=item_text,
                chunk_order=0,
                embedding=embed_text(item_text),
                metadata_json={
                    "tweet_url": item.url,
                    "tweet_id": item.tweet_id,
                    "author_handle": item.author_handle,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "source_type": "x_item",
                },
            )
            db.add(item_chunk)

    thread_id = None
    if payload.capture_type == "thread":
        captured_at = _ensure_utc(items_for_request[0].captured_at if items_for_request else datetime.now(timezone.utc))
        thread = XThread(
            user_id=user.id,
            root_tweet_id=payload.root_tweet_id,
            root_url=payload.root_tweet_url or payload.page_url,
            title=build_thread_title(items_for_request, payload.root_tweet_url or payload.page_url),
            captured_at=captured_at or datetime.now(timezone.utc),
            is_partial=payload.is_partial,
            partial_reason=payload.partial_reason,
        )
        db.add(thread)
        db.flush()
        thread_id = thread.id

        for item in items_for_request:
            link_exists = db.execute(
                select(XThreadItem).where(XThreadItem.thread_id == thread.id, XThreadItem.item_id == item.id)
            ).scalar_one_or_none()
            if link_exists is None:
                db.add(XThreadItem(thread_id=thread.id, item_id=item.id))

        macro_text = build_thread_macro_chunk_text(items_for_request)
        if macro_text:
            db.add(
                Chunk(
                    user_id=user.id,
                    source_type="x_thread",
                    source_id=thread.id,
                    chunk_text=macro_text,
                    chunk_order=0,
                    embedding=embed_text(macro_text),
                    metadata_json={
                        "thread_id": str(thread.id),
                        "tweet_url": payload.root_tweet_url or payload.page_url,
                        "tweet_id": payload.root_tweet_id,
                        "author_handle": items_for_request[0].author_handle if items_for_request else None,
                        "created_at": captured_at.isoformat() if captured_at else None,
                        "source_type": "x_thread",
                        "is_partial": payload.is_partial,
                    },
                )
            )

    db.commit()

    return IngestXResponse(
        thread_id=thread_id,
        item_ids=item_ids,
        stored_count=stored_count,
        is_partial=payload.is_partial,
    )
