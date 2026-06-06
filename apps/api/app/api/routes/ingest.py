from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.orm import Session

from app.api.deps import AuthUser, get_auth_user
from app.db.models import Chunk, XFolder, XItem, XThread, XThreadCapture, XThreadCaptureItem, XThreadItem
from app.db.session import get_db
from app.schemas.ingest import IngestXRequest, IngestXResponse
from app.services.embeddings import embed_many, embed_text
from app.services.ingest import (
    build_article_chunk_texts,
    build_item_chunk_text,
    build_thread_macro_chunk_text,
    build_thread_title,
    coalesce_capture_time,
    normalize_article_id,
    normalize_tweet_id,
    stable_item_hash,
)
from app.services.openai_client import OpenAIServiceError

router = APIRouter()


def _ensure_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _find_existing_thread(
    *,
    db: Session,
    user_id,
    root_tweet_id: str | None,
    root_url: str | None,
) -> XThread | None:
    if root_tweet_id:
        stmt = (
            select(XThread)
            .where(
                XThread.user_id == user_id,
                or_(
                    XThread.root_tweet_id == root_tweet_id,
                    and_(XThread.root_tweet_id.is_(None), XThread.root_url == root_url),
                ),
            )
            .order_by(XThread.captured_at.desc())
            .limit(1)
        )
        return db.execute(stmt).scalars().first()

    if root_url:
        stmt = (
            select(XThread)
            .where(XThread.user_id == user_id, XThread.root_tweet_id.is_(None), XThread.root_url == root_url)
            .order_by(XThread.captured_at.desc())
            .limit(1)
        )
        return db.execute(stmt).scalars().first()

    return None


def _tweet_chunk_metadata(item: XItem) -> dict[str, str | None]:
    return {
        "tweet_url": item.url,
        "tweet_id": item.tweet_id,
        "author_handle": item.author_handle,
        "created_at": item.created_at.isoformat() if item.created_at else None,
        "source_type": "x_item",
    }


@router.post("/ingest/x", response_model=IngestXResponse)
def ingest_x(
    payload: IngestXRequest,
    auth_user: AuthUser = Depends(get_auth_user),
    db: Session = Depends(get_db),
) -> IngestXResponse:
    user = auth_user.user
    folder_id = payload.folder_id

    if folder_id is not None:
        folder = db.execute(select(XFolder).where(XFolder.id == folder_id, XFolder.user_id == user.id)).scalar_one_or_none()
        if folder is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")

    seen_tweet_ids: set[str] = set()
    item_ids = []
    items_for_request: list[XItem] = []
    stored_count = 0

    if payload.capture_type == "article":
        if payload.article is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="article payload is required when capture_type='article'",
            )

        article = payload.article
        article_id = normalize_article_id(article.article_id, article.url, article.title, article.text)
        item = db.execute(
            select(XItem).where(XItem.user_id == user.id, XItem.tweet_id == article_id)
        ).scalar_one_or_none()

        article_raw = dict(article.json_raw or {})
        article_raw.update(
            {
                "source_kind": "article",
                "title": article.title,
                "article_id": article_id,
            }
        )
        article_author_handle = article.author_handle or "unknown"

        if item is None:
            item = XItem(
                user_id=user.id,
                folder_id=folder_id,
                tweet_id=article_id,
                url=article.url,
                author_handle=article_author_handle,
                author_name=article.author_name,
                created_at=_ensure_utc(article.created_at),
                captured_at=_ensure_utc(coalesce_capture_time(article.captured_at)) or datetime.now(timezone.utc),
                text=article.text,
                quoted_json=None,
                json_raw=article_raw,
                hash=stable_item_hash(user.id, article_id, article.url, article.text),
            )
            db.add(item)
            db.flush()
            stored_count += 1
        else:
            item.url = article.url
            item.author_handle = article_author_handle
            item.author_name = article.author_name
            item.created_at = _ensure_utc(article.created_at)
            item.captured_at = _ensure_utc(coalesce_capture_time(article.captured_at)) or datetime.now(timezone.utc)
            item.text = article.text
            item.json_raw = article_raw
            item.hash = stable_item_hash(user.id, article_id, article.url, article.text)
            if folder_id is not None:
                item.folder_id = folder_id
            db.add(item)
            db.flush()
        db.execute(
            delete(Chunk).where(
                Chunk.user_id == user.id,
                Chunk.source_type == "x_item",
                Chunk.source_id == item.id,
            )
        )

        item_chunk_texts = build_article_chunk_texts(item)
        try:
            item_embeddings = embed_many(item_chunk_texts)
        except OpenAIServiceError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

        for idx, (item_text, item_embedding) in enumerate(zip(item_chunk_texts, item_embeddings)):
            item_chunk = Chunk(
                user_id=user.id,
                source_type="x_item",
                source_id=item.id,
                chunk_text=item_text,
                chunk_order=idx,
                embedding=item_embedding,
                metadata_json={
                    "tweet_url": item.url,
                    "tweet_id": item.tweet_id,
                    "author_handle": item.author_handle,
                    "created_at": item.created_at.isoformat() if item.created_at else None,
                    "source_type": "x_item",
                    "source_kind": "article",
                    "title": article.title,
                    "chunk_order": idx,
                    "chunk_total": len(item_chunk_texts),
                },
            )
            db.add(item_chunk)

        db.commit()
        return IngestXResponse(
            thread_id=None,
            thread_version=None,
            item_ids=[item.id],
            stored_count=stored_count,
            is_partial=payload.is_partial,
        )

    for tw in payload.tweets:
        tweet_id = normalize_tweet_id(tw.tweet_id, tw.url, tw.text)
        if tweet_id in seen_tweet_ids:
            continue
        seen_tweet_ids.add(tweet_id)

        item = db.execute(
            select(XItem).where(XItem.user_id == user.id, XItem.tweet_id == tweet_id)
        ).scalar_one_or_none()

        captured_at = _ensure_utc(coalesce_capture_time(tw.captured_at)) or datetime.now(timezone.utc)
        created_at = _ensure_utc(tw.created_at)
        quoted_json = tw.quoted.model_dump(mode="json") if tw.quoted else None

        if item is None:
            item = XItem(
                user_id=user.id,
                folder_id=folder_id,
                tweet_id=tweet_id,
                url=tw.url,
                author_handle=tw.author_handle,
                author_name=tw.author_name,
                created_at=created_at,
                captured_at=captured_at,
                text=tw.text,
                quoted_json=quoted_json,
                json_raw=tw.json_raw,
                hash=stable_item_hash(user.id, tweet_id, tw.url, tw.text),
            )
            stored_count += 1
        else:
            item.url = tw.url
            item.author_handle = tw.author_handle
            item.author_name = tw.author_name
            item.created_at = created_at
            item.captured_at = captured_at
            item.text = tw.text
            item.quoted_json = quoted_json
            item.json_raw = tw.json_raw
            if folder_id is not None:
                item.folder_id = folder_id

        item_text = build_item_chunk_text(item)
        item.hash = stable_item_hash(user.id, tweet_id, item.url, item_text)
        db.add(item)
        db.flush()

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

        chunk_metadata = _tweet_chunk_metadata(item)
        if existing_chunk is None or existing_chunk.chunk_text != item_text:
            try:
                item_embedding = embed_text(item_text)
            except OpenAIServiceError as exc:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

            if existing_chunk is None:
                existing_chunk = Chunk(
                    user_id=user.id,
                    source_type="x_item",
                    source_id=item.id,
                    chunk_text=item_text,
                    chunk_order=0,
                    embedding=item_embedding,
                    metadata_json=chunk_metadata,
                )
            else:
                existing_chunk.chunk_text = item_text
                existing_chunk.embedding = item_embedding
                existing_chunk.metadata_json = chunk_metadata
            db.add(existing_chunk)
        elif existing_chunk.metadata_json != chunk_metadata:
            existing_chunk.metadata_json = chunk_metadata
            db.add(existing_chunk)

    thread_id = None
    thread_version = None
    if payload.capture_type == "thread":
        root_url = payload.root_tweet_url or payload.page_url
        captured_at = _ensure_utc(items_for_request[0].captured_at if items_for_request else datetime.now(timezone.utc))
        thread = _find_existing_thread(
            db=db,
            user_id=user.id,
            root_tweet_id=payload.root_tweet_id,
            root_url=root_url,
        )
        if thread is None:
            thread = XThread(
                user_id=user.id,
                folder_id=folder_id,
                root_tweet_id=payload.root_tweet_id,
                root_url=root_url,
                title=build_thread_title(items_for_request, root_url),
                captured_at=captured_at or datetime.now(timezone.utc),
                capture_version=1,
                is_partial=payload.is_partial,
                partial_reason=payload.partial_reason,
            )
            db.add(thread)
            db.flush()
        else:
            thread.root_tweet_id = payload.root_tweet_id or thread.root_tweet_id
            thread.root_url = root_url or thread.root_url
            thread.title = build_thread_title(items_for_request, root_url)
            thread.captured_at = captured_at or datetime.now(timezone.utc)
            thread.capture_version += 1
            if folder_id is not None:
                thread.folder_id = folder_id
            thread.is_partial = payload.is_partial
            thread.partial_reason = payload.partial_reason
            db.add(thread)
            db.flush()

            db.execute(delete(XThreadItem).where(XThreadItem.thread_id == thread.id))
            db.execute(
                delete(Chunk).where(
                    Chunk.user_id == user.id,
                    Chunk.source_type == "x_thread",
                    Chunk.source_id == thread.id,
                )
            )

        thread_id = thread.id
        thread_version = thread.capture_version

        for item in items_for_request:
            db.add(XThreadItem(thread_id=thread.id, item_id=item.id))

        macro_text = build_thread_macro_chunk_text(items_for_request)
        capture = XThreadCapture(
            thread_id=thread.id,
            user_id=user.id,
            capture_version=thread.capture_version,
            root_tweet_id=thread.root_tweet_id,
            root_url=thread.root_url,
            title=thread.title,
            captured_at=thread.captured_at,
            is_partial=thread.is_partial,
            partial_reason=thread.partial_reason,
            macro_chunk_text=macro_text or None,
        )
        db.add(capture)
        db.flush()

        for item_order, item in enumerate(items_for_request):
            db.add(
                XThreadCaptureItem(
                    capture_id=capture.id,
                    item_order=item_order,
                    item_id=item.id,
                    tweet_id=item.tweet_id,
                    url=item.url,
                    author_handle=item.author_handle,
                    author_name=item.author_name,
                    created_at=item.created_at,
                    captured_at=item.captured_at,
                    text=item.text,
                    quoted_json=item.quoted_json,
                    json_raw=item.json_raw,
                    hash=item.hash,
                )
            )

        if macro_text:
            try:
                thread_embedding = embed_text(macro_text)
            except OpenAIServiceError as exc:
                raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

            db.add(
                Chunk(
                    user_id=user.id,
                    source_type="x_thread",
                    source_id=thread.id,
                    chunk_text=macro_text,
                    chunk_order=0,
                    embedding=thread_embedding,
                    metadata_json={
                        "thread_id": str(thread.id),
                        "tweet_url": root_url,
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
        thread_version=thread_version,
        item_ids=item_ids,
        stored_count=stored_count,
        is_partial=payload.is_partial,
    )
