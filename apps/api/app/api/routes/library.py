from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_any_authenticated_user
from app.db.models import XItem, XThread, XThreadItem
from app.db.models import User
from app.db.session import get_db
from app.schemas.ingest import LibraryItem, LibraryThreadListItem, ThreadDetailResponse

router = APIRouter()


@router.get("/me")
def me(user: User = Depends(get_any_authenticated_user)) -> dict[str, str | None]:
    return {
        "user_id": str(user.id),
        "clerk_user_id": user.clerk_user_id,
        "email": user.email,
    }


@router.get("/library/items", response_model=list[LibraryItem])
def list_items(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> list[LibraryItem]:
    stmt = (
        select(XItem)
        .where(XItem.user_id == user.id)
        .order_by(XItem.captured_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = db.execute(stmt).scalars().all()
    return [LibraryItem.model_validate(item) for item in items]


@router.get("/library/threads", response_model=list[LibraryThreadListItem])
def list_threads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> list[LibraryThreadListItem]:
    stmt = (
        select(
            XThread.id,
            XThread.root_tweet_id,
            XThread.root_url,
            XThread.title,
            XThread.captured_at,
            XThread.capture_version,
            XThread.is_partial,
            func.count(XThreadItem.item_id).label("item_count"),
        )
        .outerjoin(XThreadItem, XThreadItem.thread_id == XThread.id)
        .where(XThread.user_id == user.id)
        .group_by(XThread.id)
        .order_by(XThread.captured_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).all()
    return [
        LibraryThreadListItem(
            id=row.id,
            root_tweet_id=row.root_tweet_id,
            root_url=row.root_url,
            title=row.title,
            captured_at=row.captured_at,
            capture_version=row.capture_version,
            is_partial=row.is_partial,
            item_count=row.item_count,
        )
        for row in rows
    ]


@router.get("/library/threads/{thread_id}", response_model=ThreadDetailResponse)
def get_thread(
    thread_id: UUID,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> ThreadDetailResponse:
    thread_row = db.execute(
        select(
            XThread.id,
            XThread.root_tweet_id,
            XThread.root_url,
            XThread.title,
            XThread.captured_at,
            XThread.capture_version,
            XThread.is_partial,
            func.count(XThreadItem.item_id).label("item_count"),
        )
        .outerjoin(XThreadItem, XThreadItem.thread_id == XThread.id)
        .where(XThread.id == thread_id, XThread.user_id == user.id)
        .group_by(XThread.id)
    ).first()

    if thread_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    item_stmt = (
        select(XItem)
        .join(XThreadItem, XThreadItem.item_id == XItem.id)
        .where(XThreadItem.thread_id == thread_id, XItem.user_id == user.id)
        .order_by(XItem.captured_at.asc())
    )
    items = db.execute(item_stmt).scalars().all()

    thread = LibraryThreadListItem(
        id=thread_row.id,
        root_tweet_id=thread_row.root_tweet_id,
        root_url=thread_row.root_url,
        title=thread_row.title,
        captured_at=thread_row.captured_at,
        capture_version=thread_row.capture_version,
        is_partial=thread_row.is_partial,
        item_count=thread_row.item_count,
    )
    return ThreadDetailResponse(thread=thread, items=[LibraryItem.model_validate(item) for item in items])
