from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.api.deps import get_any_authenticated_user
from app.core.config import get_settings
from app.db.models import User, XApiUsage, XFolder, XIntegration, XOAuthState
from app.db.session import get_db
from app.schemas.x_integration import (
    XAuthorizeResponse,
    XBookmarkSyncResponse,
    XSourceRequest,
    XSourceResponse,
    XStatusResponse,
)
from app.services.x_api import (
    XApiClient,
    XApiError,
    build_authorization_url,
    exchange_authorization_code,
    get_x_client,
)
from app.services.x_crypto import decrypt_x_secret, encrypt_x_secret
from app.services.x_ingestion import is_x_article_url, parse_x_post_id, save_article_link, save_post, sync_bookmarks

router = APIRouter()


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _challenge(verifier: str) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")


def _integration(db: Session, user_id) -> XIntegration:
    integration = db.execute(select(XIntegration).where(XIntegration.user_id == user_id)).scalar_one_or_none()
    if not integration:
        raise HTTPException(status_code=409, detail="Connect your X account before saving or syncing X content.")
    return integration


def _raise_x(exc: XApiError) -> None:
    raise HTTPException(status_code=exc.status_code, detail={"code": exc.code, "message": str(exc)}) from exc


@router.get("/integrations/x/status", response_model=XStatusResponse)
def x_status(user: User = Depends(get_any_authenticated_user), db: Session = Depends(get_db)) -> XStatusResponse:
    integration = db.execute(select(XIntegration).where(XIntegration.user_id == user.id)).scalar_one_or_none()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    reads = int(
        db.execute(
            select(func.coalesce(func.sum(XApiUsage.returned_post_count), 0)).where(
                XApiUsage.user_id == user.id, XApiUsage.created_at >= month_start
            )
        ).scalar_one()
    )
    settings = get_settings()
    if not integration:
        return XStatusResponse(
            connected=False,
            status="disconnected",
            monthly_post_reads=reads,
            monthly_post_read_budget=settings.x_monthly_post_read_budget,
        )
    return XStatusResponse(
        connected=integration.status == "connected",
        status=integration.status,
        x_user_id=integration.x_user_id,
        x_username=integration.x_username,
        granted_scopes=integration.granted_scopes,
        connected_at=integration.connected_at,
        last_bookmark_sync_at=integration.last_bookmark_sync_at,
        last_bookmark_sync_result=integration.last_bookmark_sync_result,
        monthly_post_reads=reads,
        monthly_post_read_budget=settings.x_monthly_post_read_budget,
    )


@router.post("/integrations/x/authorize", response_model=XAuthorizeResponse)
def x_authorize(user: User = Depends(get_any_authenticated_user), db: Session = Depends(get_db)) -> XAuthorizeResponse:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=10)
    state = secrets.token_urlsafe(48)
    verifier = secrets.token_urlsafe(64)
    db.add(
        XOAuthState(
            user_id=user.id,
            state_hash=_hash(state),
            pkce_verifier_encrypted=encrypt_x_secret(verifier),
            expires_at=expires,
        )
    )
    db.commit()
    try:
        authorization_url = build_authorization_url(state=state, code_challenge=_challenge(verifier))
    except XApiError as exc:
        _raise_x(exc)
    return XAuthorizeResponse(authorization_url=authorization_url, expires_at=expires)


@router.get("/integrations/x/callback")
def x_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: Session = Depends(get_db),
) -> RedirectResponse:
    now = datetime.now(timezone.utc)
    oauth_state = db.execute(select(XOAuthState).where(XOAuthState.state_hash == _hash(state)).with_for_update()).scalar_one_or_none()
    if not oauth_state or oauth_state.consumed_at is not None:
        raise HTTPException(status_code=400, detail="Invalid or already-consumed X OAuth state.")
    expires = oauth_state.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires <= now:
        raise HTTPException(status_code=400, detail="X OAuth state expired. Start the connection flow again.")
    oauth_state.consumed_at = now
    db.add(oauth_state)
    db.commit()

    try:
        token = exchange_authorization_code(code=code, code_verifier=decrypt_x_secret(oauth_state.pkce_verifier_encrypted))
        integration = db.execute(select(XIntegration).where(XIntegration.user_id == oauth_state.user_id)).scalar_one_or_none()
        if not integration:
            integration = XIntegration(
                user_id=oauth_state.user_id,
                x_user_id="pending",
                access_token_encrypted=encrypt_x_secret(str(token["access_token"])),
                refresh_token_encrypted=encrypt_x_secret(str(token["refresh_token"])) if token.get("refresh_token") else None,
                granted_scopes=str(token.get("scope") or "").split(),
                status="connected",
            )
        else:
            integration.access_token_encrypted = encrypt_x_secret(str(token["access_token"]))
            integration.refresh_token_encrypted = (
                encrypt_x_secret(str(token["refresh_token"])) if token.get("refresh_token") else integration.refresh_token_encrypted
            )
            integration.granted_scopes = str(token.get("scope") or "").split()
            integration.status = "connected"
        integration.access_token_expires_at = now + timedelta(seconds=int(token.get("expires_in", 7200)))
        client = XApiClient(db=db, user_id=oauth_state.user_id, integration=integration)
        profile = client.get_me()
        integration.x_user_id = str(profile["id"])
        integration.x_username = profile.get("username")
        db.add(integration)
        db.commit()
    except XApiError as exc:
        _raise_x(exc)
    query = urlencode({"connected": "1"})
    return RedirectResponse(f"{get_settings().x_integration_settings_url}?{query}", status_code=302)


@router.delete("/integrations/x")
def x_disconnect(user: User = Depends(get_any_authenticated_user), db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(delete(XIntegration).where(XIntegration.user_id == user.id))
    db.commit()
    return {"status": "disconnected"}


@router.post("/integrations/x/bookmarks/sync", response_model=XBookmarkSyncResponse)
def x_bookmarks_sync(
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> XBookmarkSyncResponse:
    integration = _integration(db, user.id)
    client = get_x_client(db=db, user_id=user.id, integration=integration)
    try:
        return sync_bookmarks(
            db=db,
            user=user,
            integration=integration,
            client=client,
            max_posts=get_settings().x_bookmark_sync_post_limit,
        )
    except XApiError as exc:
        _raise_x(exc)


@router.post("/sources/x", response_model=XSourceResponse)
def create_x_source(
    payload: XSourceRequest,
    user: User = Depends(get_any_authenticated_user),
    db: Session = Depends(get_db),
) -> XSourceResponse:
    if payload.folder_id is not None:
        folder = db.execute(select(XFolder.id).where(XFolder.id == payload.folder_id, XFolder.user_id == user.id)).scalar_one_or_none()
        if not folder:
            raise HTTPException(status_code=404, detail="Folder not found.")
    integration = _integration(db, user.id)
    if is_x_article_url(payload.url):
        return save_article_link(db=db, user=user, url=payload.url.strip(), folder_id=payload.folder_id)
    post_id = parse_x_post_id(payload.url)
    try:
        return save_post(
            db=db,
            user=user,
            client=get_x_client(db=db, user_id=user.id, integration=integration),
            post_id=post_id,
            folder_id=payload.folder_id,
            mode=payload.mode,
        )
    except XApiError as exc:
        _raise_x(exc)
