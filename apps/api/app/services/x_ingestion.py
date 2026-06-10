from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import AuthUser
from app.api.routes.ingest import ingest_x
from app.db.models import (
    Chunk,
    User,
    XBookmarkFolderMapping,
    XFolder,
    XIntegration,
    XItem,
    XThread,
    XThreadItem,
)
from app.schemas.ingest import IngestArticlePayload, IngestTweetPayload, IngestXRequest, QuotedTweetPayload
from app.schemas.x_integration import XBookmarkSyncResponse, XSourceResponse
from app.services.x_api import XApiClient, XApiError, XPage
from app.services.embeddings import embed_text
from app.services.ingest import build_thread_macro_chunk_text

POST_URL_RE = re.compile(r"^https://(?:www\.)?(?:x|twitter)\.com/[A-Za-z0-9_]{1,15}/status/(\d+)(?:[/?#].*)?$", re.I)
ARTICLE_URL_RE = re.compile(r"^https://(?:www\.)?(?:x|twitter)\.com/i/articles?/", re.I)


def parse_x_post_id(value: str) -> str:
    cleaned = (value or "").strip()
    if cleaned.isdigit():
        return cleaned
    if ARTICLE_URL_RE.match(cleaned):
        raise HTTPException(status_code=422, detail="Full-body X Article capture is unsupported; store the article URL as a link-only record.")
    match = POST_URL_RE.match(cleaned)
    if not match:
        raise HTTPException(status_code=422, detail="Provide an X post ID or a canonical x.com/<user>/status/<id> URL.")
    return match.group(1)


def is_x_article_url(value: str) -> bool:
    return bool(ARTICLE_URL_RE.match((value or "").strip()))


def _authors(includes: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(user.get("id")): user for user in includes.get("users") or [] if isinstance(user, dict)}


def _referenced_posts(includes: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(post.get("id")): post for post in includes.get("tweets") or [] if isinstance(post, dict)}


def _quoted_payload(post: dict[str, Any], includes: dict[str, Any]) -> QuotedTweetPayload | None:
    refs = _referenced_posts(includes)
    authors = _authors(includes)
    quoted_ref = next((ref for ref in post.get("referenced_tweets") or [] if ref.get("type") == "quoted"), None)
    quoted = refs.get(str(quoted_ref.get("id"))) if quoted_ref else None
    if not quoted:
        return None
    author = authors.get(str(quoted.get("author_id"))) or {}
    username = author.get("username") or "unknown"
    return QuotedTweetPayload(
        tweet_id=str(quoted["id"]),
        url=f"https://x.com/{username}/status/{quoted['id']}",
        text=str(quoted.get("text") or ""),
        author_handle=username,
        author_name=author.get("name"),
        created_at=quoted.get("created_at"),
    )


def normalized_payload(post: dict[str, Any], includes: dict[str, Any]) -> IngestTweetPayload:
    authors = _authors(includes)
    author = authors.get(str(post.get("author_id"))) or {}
    username = str(author.get("username") or "unknown")
    now = datetime.now(timezone.utc)
    return IngestTweetPayload(
        tweet_id=str(post["id"]),
        url=f"https://x.com/{username}/status/{post['id']}",
        author_handle=username,
        author_name=author.get("name"),
        created_at=post.get("created_at"),
        text=str(post.get("text") or ""),
        quoted=_quoted_payload(post, includes),
        captured_at=now,
        json_raw={
            "source_kind": "post",
            "external_source": "x_api",
            "conversation_id": post.get("conversation_id"),
            "author_id": post.get("author_id"),
            "in_reply_to_user_id": post.get("in_reply_to_user_id"),
            "referenced_tweets": post.get("referenced_tweets") or [],
            "edit_history_tweet_ids": post.get("edit_history_tweet_ids") or [],
        },
    )


def _mark_verified(db: Session, *, user_id: UUID, post_ids: list[str]) -> None:
    now = datetime.now(timezone.utc)
    items = db.execute(select(XItem).where(XItem.user_id == user_id, XItem.tweet_id.in_(post_ids))).scalars().all()
    for item in items:
        item.external_source = "x"
        item.external_id = item.tweet_id
        item.content_status = "active"
        item.last_verified_at = now
        item.unavailable_reason = None
        db.add(item)
        chunks = db.execute(
            select(Chunk).where(Chunk.user_id == user_id, Chunk.source_type == "x_item", Chunk.source_id == item.id)
        ).scalars().all()
        for chunk in chunks:
            chunk.metadata_json = {
                **(chunk.metadata_json or {}),
                "content_status": "active",
                "last_verified_at": now.isoformat(),
            }
            db.add(chunk)
    db.commit()


def save_article_link(*, db: Session, user: User, url: str, folder_id: UUID | None) -> XSourceResponse:
    article_id = f"article_link_{hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]}"
    now = datetime.now(timezone.utc)
    result = ingest_x(
        payload=IngestXRequest(
            capture_type="article",
            page_url=url,
            article=IngestArticlePayload(
                article_id=article_id,
                url=url,
                title="X Article (link only)",
                author_handle="unknown",
                text="Full-body X Article capture is unsupported. Open the source URL on X.",
                captured_at=now,
                json_raw={"source_kind": "article", "capture_mode": "link_only"},
            ),
            captured_count=1,
            folder_id=folder_id,
        ),
        auth_user=AuthUser(user=user),
        db=db,
    )
    item = db.execute(select(XItem).where(XItem.user_id == user.id, XItem.tweet_id == article_id)).scalar_one()
    item.external_source = "x"
    item.external_id = article_id
    item.content_status = "unsupported"
    item.last_verified_at = now
    item.unavailable_reason = "Full-body X Article capture is unsupported by the official integration."
    db.add(item)
    for chunk in db.execute(
        select(Chunk).where(Chunk.user_id == user.id, Chunk.source_type == "x_item", Chunk.source_id == item.id)
    ).scalars():
        chunk.metadata_json = {**(chunk.metadata_json or {}), "content_status": "unsupported"}
        db.add(chunk)
    db.commit()
    return XSourceResponse(item_ids=result.item_ids, created=result.stored_count)


def ingest_page(
    *,
    db: Session,
    user: User,
    page: XPage,
    folder_id: UUID | None = None,
    as_thread: bool = False,
    root_post_id: str | None = None,
    partial_reason: str | None = None,
) -> XSourceResponse:
    posts = page.posts
    if not posts:
        raise XApiError("The X post is unavailable or inaccessible with this account.", code="unavailable", status_code=404)
    tweets = [normalized_payload(post, page.includes) for post in posts]
    root = root_post_id or str(posts[0]["id"])
    payload = IngestXRequest(
        capture_type="thread" if as_thread else "tweet",
        page_url=f"https://x.com/i/status/{root}",
        root_tweet_id=root,
        root_tweet_url=f"https://x.com/i/status/{root}",
        tweets=tweets,
        captured_count=len(tweets),
        folder_id=folder_id,
        is_partial=bool(partial_reason),
        partial_reason=partial_reason,
    )
    before = {
        item.tweet_id: item.hash
        for item in db.execute(select(XItem).where(XItem.user_id == user.id, XItem.tweet_id.in_([str(p["id"]) for p in posts]))).scalars()
    }
    result = ingest_x(payload=payload, auth_user=AuthUser(user=user), db=db)
    _mark_verified(db, user_id=user.id, post_ids=[str(post["id"]) for post in posts])
    updated = sum(
        1
        for item in db.execute(select(XItem).where(XItem.user_id == user.id, XItem.tweet_id.in_(list(before)))).scalars()
        if before.get(item.tweet_id) != item.hash
    )
    changed_at = datetime.now(timezone.utc)
    changed_items = db.execute(
        select(XItem).where(XItem.user_id == user.id, XItem.tweet_id.in_([str(post["id"]) for post in posts]))
    ).scalars().all()
    for item in changed_items:
        if item.tweet_id not in before or before.get(item.tweet_id) != item.hash:
            item.last_content_change_at = changed_at
            db.add(item)
    db.commit()
    return XSourceResponse(
        item_ids=result.item_ids,
        thread_id=result.thread_id,
        thread_version=result.thread_version,
        created=result.stored_count,
        updated=updated,
        is_partial=result.is_partial,
        partial_reason=partial_reason,
    )


def save_post(
    *,
    db: Session,
    user: User,
    client: XApiClient,
    post_id: str,
    folder_id: UUID | None,
    mode: str,
) -> XSourceResponse:
    selected = client.get_post(post_id)
    if mode == "post":
        return ingest_page(db=db, user=user, page=selected, folder_id=folder_id)

    selected_post = selected.posts[0] if selected.posts else None
    if not selected_post:
        raise XApiError("The selected X post is unavailable.", code="unavailable", status_code=404)
    conversation_id = str(selected_post.get("conversation_id") or selected_post["id"])
    all_posts = {str(selected_post["id"]): selected_post}
    includes = {"users": list(selected.includes.get("users") or []), "tweets": list(selected.includes.get("tweets") or [])}
    root_post = selected_post
    if conversation_id != str(selected_post["id"]):
        root_page = client.get_post(conversation_id)
        if root_page.posts:
            root_post = root_page.posts[0]
            all_posts[str(root_post["id"])] = root_post
            for key in ("users", "tweets"):
                includes[key].extend(root_page.includes.get(key) or [])
    author_id = str(root_post.get("author_id") or "")
    next_token: str | None = None
    pages = 0
    partial_reason = "X conversation search is best effort and cannot guarantee completeness."
    while pages < 10:
        page = client.search_conversation(conversation_id, next_token=next_token)
        for post in page.posts:
            all_posts[str(post["id"])] = post
        for key in ("users", "tweets"):
            includes[key].extend(page.includes.get(key) or [])
        pages += 1
        next_token = page.next_token
        if not next_token:
            break
    if next_token:
        partial_reason = "Thread search pagination limit reached; capture is partial."
    ordered = _root_author_thread_posts(all_posts=all_posts, root_id=conversation_id, author_id=author_id)
    return ingest_page(
        db=db,
        user=user,
        page=XPage(posts=ordered, includes=includes),
        folder_id=folder_id,
        as_thread=True,
        root_post_id=conversation_id,
        partial_reason=partial_reason,
    )


def _root_author_thread_posts(*, all_posts: dict[str, dict[str, Any]], root_id: str, author_id: str) -> list[dict[str, Any]]:
    included = {root_id}
    changed = True
    while changed:
        changed = False
        for post_id, post in all_posts.items():
            if post_id in included or str(post.get("author_id") or "") != author_id:
                continue
            parent_ids = {
                str(ref.get("id"))
                for ref in post.get("referenced_tweets") or []
                if ref.get("type") == "replied_to" and ref.get("id")
            }
            if parent_ids & included:
                included.add(post_id)
                changed = True
    return sorted(
        (all_posts[post_id] for post_id in included if post_id in all_posts),
        key=lambda post: (str(post.get("created_at") or ""), str(post["id"])),
    )


def _mapped_folder(db: Session, *, user: User, x_folder_id: str, x_folder_name: str) -> XFolder:
    mapping = db.execute(
        select(XBookmarkFolderMapping).where(
            XBookmarkFolderMapping.user_id == user.id, XBookmarkFolderMapping.x_folder_id == x_folder_id
        )
    ).scalar_one_or_none()
    if mapping:
        return db.execute(select(XFolder).where(XFolder.id == mapping.local_folder_id)).scalar_one()
    base_name = f"X Bookmarks: {x_folder_name}"[:120]
    name = base_name
    suffix = 2
    while db.execute(select(XFolder.id).where(XFolder.user_id == user.id, func.lower(XFolder.name) == name.lower())).scalar_one_or_none():
        name = f"{base_name[:110]} ({suffix})"
        suffix += 1
    folder = XFolder(user_id=user.id, name=name)
    db.add(folder)
    db.flush()
    db.add(
        XBookmarkFolderMapping(
            user_id=user.id,
            x_folder_id=x_folder_id,
            x_folder_name=x_folder_name,
            local_folder_id=folder.id,
        )
    )
    db.commit()
    return folder


def sync_bookmarks(*, db: Session, user: User, integration: XIntegration, client: XApiClient, max_posts: int) -> XBookmarkSyncResponse:
    result = XBookmarkSyncResponse()
    token: str | None = None
    while result.fetched < max_posts:
        page = client.get_bookmarks(pagination_token=token, max_results=min(100, max_posts - result.fetched))
        for post in page.posts:
            result.fetched += 1
            try:
                saved = ingest_page(db=db, user=user, page=XPage(posts=[post], includes=page.includes))
                result.created += saved.created
                result.updated += saved.updated
            except XApiError:
                result.unavailable += 1
            except Exception:
                result.failed += 1
        token = page.next_token
        if not token:
            break
    if token:
        result.partial = True

    try:
        for folder_data in client.get_bookmark_folders():
            folder_id = str(folder_data.get("id") or "")
            if not folder_id:
                continue
            local = _mapped_folder(
                db, user=user, x_folder_id=folder_id, x_folder_name=str(folder_data.get("name") or "Untitled")
            )
            result.folders_mapped += 1
            folder_token: str | None = None
            while True:
                folder_page = client.get_bookmark_folder_posts(folder_id, pagination_token=folder_token)
                for post in folder_page.posts:
                    ingest_page(db=db, user=user, page=XPage(posts=[post], includes=folder_page.includes), folder_id=local.id)
                folder_token = folder_page.next_token
                if not folder_token:
                    break
    except XApiError:
        result.partial = True

    integration.bookmark_sync_cursor = token
    integration.last_bookmark_sync_at = datetime.now(timezone.utc)
    integration.last_bookmark_sync_result = result.model_dump(mode="json")
    db.add(integration)
    db.commit()
    return result


def revalidate_user_sources(*, db: Session, user: User, client: XApiClient) -> dict[str, int]:
    counts = {"verified": 0, "updated": 0, "unavailable": 0}
    items = db.execute(
        select(XItem).where(
            XItem.user_id == user.id,
            XItem.external_source == "x",
            XItem.content_status.in_(["active", "pending_verification"]),
            XItem.tweet_id.not_like("synthetic_%"),
        )
    ).scalars().all()
    by_id = {item.tweet_id: item for item in items}
    ids = list(by_id)
    for start in range(0, len(ids), 100):
        batch = ids[start : start + 100]
        page = client.get_posts(batch)
        returned = {str(post["id"]) for post in page.posts}
        for post in page.posts:
            saved = ingest_page(db=db, user=user, page=XPage(posts=[post], includes=page.includes))
            counts["verified"] += 1
            counts["updated"] += saved.updated
            if saved.updated:
                _rebuild_current_threads_for_item(db=db, user=user, item_id=saved.item_ids[0])
        now = datetime.now(timezone.utc)
        for missing in set(batch) - returned:
            item = by_id[missing]
            item.content_status = "unavailable"
            item.unavailable_reason = "Not returned by X batch lookup."
            item.last_verified_at = now
            db.add(item)
            chunks = db.execute(
                select(Chunk).where(
                    Chunk.user_id == user.id,
                    Chunk.source_type == "x_item",
                    Chunk.source_id == item.id,
                )
            ).scalars().all()
            for chunk in chunks:
                chunk.metadata_json = {
                    **(chunk.metadata_json or {}),
                    "content_status": "unavailable",
                    "last_verified_at": now.isoformat(),
                }
                db.add(chunk)
            counts["unavailable"] += 1
        db.commit()
    return counts


def _rebuild_current_threads_for_item(*, db: Session, user: User, item_id: UUID) -> None:
    thread_ids = db.execute(
        select(XThreadItem.thread_id).join(XThread, XThread.id == XThreadItem.thread_id).where(
            XThreadItem.item_id == item_id, XThread.user_id == user.id
        )
    ).scalars().all()
    for thread_id in thread_ids:
        items = db.execute(
            select(XItem)
            .join(XThreadItem, XThreadItem.item_id == XItem.id)
            .where(XThreadItem.thread_id == thread_id, XItem.user_id == user.id)
            .order_by(XItem.created_at.asc().nulls_last(), XItem.id.asc())
        ).scalars().all()
        macro = build_thread_macro_chunk_text(items)
        chunk = db.execute(
            select(Chunk).where(
                Chunk.user_id == user.id,
                Chunk.source_type == "x_thread",
                Chunk.source_id == thread_id,
                Chunk.chunk_order == 0,
            )
        ).scalar_one_or_none()
        if chunk and chunk.chunk_text != macro:
            chunk.chunk_text = macro
            chunk.embedding = embed_text(macro)
            db.add(chunk)
    db.commit()
