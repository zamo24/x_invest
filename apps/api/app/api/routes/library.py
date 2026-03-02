from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_any_authenticated_user
from app.db.models import User, XFolder, XItem, XThread, XThreadItem
from app.db.session import get_db
from app.schemas.folders import FolderAssignRequest, FolderAssignmentResponse, FolderCreateRequest, FolderResponse
from app.schemas.ingest import LibraryItem, LibraryThreadListItem, ThreadDetailResponse

router = APIRouter()


def _assert_folder_access(folder_id: UUID, user_id: UUID, db: Session) -> XFolder:
    folder = db.execute(select(XFolder).where(XFolder.id == folder_id, XFolder.user_id == user_id)).scalar_one_or_none()
    if folder is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Folder not found")
    return folder


def _library_item(item: XItem, folder_name: str | None) -> LibraryItem:
    source_kind = "tweet"
    title = None
    if isinstance(item.json_raw, dict):
        maybe_kind = item.json_raw.get("source_kind")
        if maybe_kind == "article":
            source_kind = "article"
        maybe_title = item.json_raw.get("title")
        if isinstance(maybe_title, str) and maybe_title.strip():
            title = maybe_title.strip()

    return LibraryItem(
        id=item.id,
        tweet_id=item.tweet_id,
        url=item.url,
        author_handle=item.author_handle,
        author_name=item.author_name,
        created_at=item.created_at,
        captured_at=item.captured_at,
        text=item.text,
        source_kind=source_kind,
        title=title,
        folder_id=item.folder_id,
        folder_name=folder_name,
    )


@router.get("/me")
def me(user: User = Depends(get_any_authenticated_user)) -> dict[str, str | None]:
    return {
        "user_id": str(user.id),
        "clerk_user_id": user.clerk_user_id,
        "email": user.email,
    }


@router.get("/library/folders", response_model=list[FolderResponse])
def list_folders(
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> list[FolderResponse]:
    item_counts = (
        select(XItem.folder_id.label("folder_id"), func.count(XItem.id).label("item_count"))
        .where(XItem.user_id == user.id, XItem.folder_id.is_not(None))
        .group_by(XItem.folder_id)
        .subquery()
    )
    thread_counts = (
        select(XThread.folder_id.label("folder_id"), func.count(XThread.id).label("thread_count"))
        .where(XThread.user_id == user.id, XThread.folder_id.is_not(None))
        .group_by(XThread.folder_id)
        .subquery()
    )

    stmt = (
        select(
            XFolder.id,
            XFolder.name,
            XFolder.created_at,
            func.coalesce(item_counts.c.item_count, 0).label("item_count"),
            func.coalesce(thread_counts.c.thread_count, 0).label("thread_count"),
        )
        .outerjoin(item_counts, item_counts.c.folder_id == XFolder.id)
        .outerjoin(thread_counts, thread_counts.c.folder_id == XFolder.id)
        .where(XFolder.user_id == user.id)
        .order_by(XFolder.name.asc())
    )

    rows = db.execute(stmt).all()
    return [
        FolderResponse(
            id=row.id,
            name=row.name,
            created_at=row.created_at,
            item_count=row.item_count,
            thread_count=row.thread_count,
        )
        for row in rows
    ]


@router.post("/library/folders", response_model=FolderResponse)
def create_folder(
    payload: FolderCreateRequest,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> FolderResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Folder name cannot be empty")

    existing = db.execute(
        select(XFolder).where(XFolder.user_id == user.id, func.lower(XFolder.name) == name.lower())
    ).scalar_one_or_none()
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Folder name already exists")

    folder = XFolder(user_id=user.id, name=name)
    db.add(folder)
    db.commit()
    db.refresh(folder)

    return FolderResponse(id=folder.id, name=folder.name, created_at=folder.created_at, item_count=0, thread_count=0)


@router.delete("/library/folders/{folder_id}")
def delete_folder(
    folder_id: UUID,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    folder = _assert_folder_access(folder_id=folder_id, user_id=user.id, db=db)
    db.delete(folder)
    db.commit()
    return {"status": "ok"}


@router.patch("/library/items/{item_id}/folder", response_model=FolderAssignmentResponse)
def assign_item_folder(
    item_id: UUID,
    payload: FolderAssignRequest,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> FolderAssignmentResponse:
    folder_name: str | None = None
    if payload.folder_id is not None:
        folder = _assert_folder_access(folder_id=payload.folder_id, user_id=user.id, db=db)
        folder_name = folder.name

    item = db.execute(select(XItem).where(XItem.id == item_id, XItem.user_id == user.id)).scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")

    item.folder_id = payload.folder_id
    db.add(item)
    db.commit()

    return FolderAssignmentResponse(id=item.id, folder_id=item.folder_id, folder_name=folder_name)


@router.patch("/library/threads/{thread_id}/folder", response_model=FolderAssignmentResponse)
def assign_thread_folder(
    thread_id: UUID,
    payload: FolderAssignRequest,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> FolderAssignmentResponse:
    folder_name: str | None = None
    if payload.folder_id is not None:
        folder = _assert_folder_access(folder_id=payload.folder_id, user_id=user.id, db=db)
        folder_name = folder.name

    thread = db.execute(select(XThread).where(XThread.id == thread_id, XThread.user_id == user.id)).scalar_one_or_none()
    if thread is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    thread.folder_id = payload.folder_id
    db.add(thread)
    db.commit()

    return FolderAssignmentResponse(id=thread.id, folder_id=thread.folder_id, folder_name=folder_name)


@router.get("/library/items", response_model=list[LibraryItem])
def list_items(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    folder_id: UUID | None = Query(default=None),
    unassigned: bool = Query(default=False),
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> list[LibraryItem]:
    if folder_id and unassigned:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="folder_id and unassigned cannot both be set")

    if folder_id:
        _assert_folder_access(folder_id=folder_id, user_id=user.id, db=db)

    stmt = (
        select(XItem, XFolder.name.label("folder_name"))
        .outerjoin(XFolder, XFolder.id == XItem.folder_id)
        .where(XItem.user_id == user.id)
    )
    if folder_id:
        stmt = stmt.where(XItem.folder_id == folder_id)
    elif unassigned:
        stmt = stmt.where(XItem.folder_id.is_(None))

    stmt = stmt.order_by(XItem.captured_at.desc()).limit(limit).offset(offset)
    rows = db.execute(stmt).all()
    return [_library_item(item=row.XItem, folder_name=row.folder_name) for row in rows]


@router.get("/library/threads", response_model=list[LibraryThreadListItem])
def list_threads(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    folder_id: UUID | None = Query(default=None),
    unassigned: bool = Query(default=False),
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> list[LibraryThreadListItem]:
    if folder_id and unassigned:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="folder_id and unassigned cannot both be set")

    if folder_id:
        _assert_folder_access(folder_id=folder_id, user_id=user.id, db=db)

    stmt = (
        select(
            XThread.id,
            XThread.root_tweet_id,
            XThread.root_url,
            XThread.title,
            XThread.captured_at,
            XThread.capture_version,
            XThread.is_partial,
            XThread.folder_id,
            XFolder.name.label("folder_name"),
            func.count(XThreadItem.item_id).label("item_count"),
            func.array_agg(func.distinct(XItem.author_handle)).label("author_handles"),
        )
        .outerjoin(XThreadItem, XThreadItem.thread_id == XThread.id)
        .outerjoin(XItem, XItem.id == XThreadItem.item_id)
        .outerjoin(XFolder, XFolder.id == XThread.folder_id)
        .where(XThread.user_id == user.id)
    )

    if folder_id:
        stmt = stmt.where(XThread.folder_id == folder_id)
    elif unassigned:
        stmt = stmt.where(XThread.folder_id.is_(None))

    stmt = stmt.group_by(XThread.id, XFolder.name).order_by(XThread.captured_at.desc()).limit(limit).offset(offset)
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
            author_handles=[handle for handle in (row.author_handles or []) if handle],
            folder_id=row.folder_id,
            folder_name=row.folder_name,
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
            XThread.folder_id,
            XFolder.name.label("folder_name"),
            func.count(XThreadItem.item_id).label("item_count"),
            func.array_agg(func.distinct(XItem.author_handle)).label("author_handles"),
        )
        .outerjoin(XThreadItem, XThreadItem.thread_id == XThread.id)
        .outerjoin(XItem, XItem.id == XThreadItem.item_id)
        .outerjoin(XFolder, XFolder.id == XThread.folder_id)
        .where(XThread.id == thread_id, XThread.user_id == user.id)
        .group_by(XThread.id, XFolder.name)
    ).first()

    if thread_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")

    item_stmt = (
        select(XItem, XFolder.name.label("folder_name"))
        .join(XThreadItem, XThreadItem.item_id == XItem.id)
        .outerjoin(XFolder, XFolder.id == XItem.folder_id)
        .where(XThreadItem.thread_id == thread_id, XItem.user_id == user.id)
        .order_by(XItem.captured_at.asc())
    )
    item_rows = db.execute(item_stmt).all()

    thread = LibraryThreadListItem(
        id=thread_row.id,
        root_tweet_id=thread_row.root_tweet_id,
        root_url=thread_row.root_url,
        title=thread_row.title,
        captured_at=thread_row.captured_at,
        capture_version=thread_row.capture_version,
        is_partial=thread_row.is_partial,
        item_count=thread_row.item_count,
        author_handles=[handle for handle in (thread_row.author_handles or []) if handle],
        folder_id=thread_row.folder_id,
        folder_name=thread_row.folder_name,
    )
    items = [_library_item(item=row.XItem, folder_name=row.folder_name) for row in item_rows]
    return ThreadDetailResponse(thread=thread, items=items)
