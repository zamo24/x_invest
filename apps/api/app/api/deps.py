from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select, or_, select
from sqlalchemy.orm import Session

from app.core.clerk_jwt import verify_clerk_jwt
from app.core.config import get_settings
from app.core.security import hash_token, is_well_formed_pat
from app.db.models import ApiToken, User
from app.db.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class ClerkIdentity:
    clerk_user_id: str
    email: str | None


@dataclass
class AuthUser:
    user: User
    token: ApiToken | None = None


def _unauthorized(detail: str = "Invalid or missing token") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def _extract_bearer_token(creds: HTTPAuthorizationCredentials | None) -> str:
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials.strip():
        raise _unauthorized("Missing Bearer authentication token.")
    return creds.credentials.strip()


def _looks_like_jwt(token: str) -> bool:
    return token.count(".") == 2


def get_auth_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    return _resolve_pat_auth(_extract_bearer_token(creds), db, request=request)


def get_current_user(auth_user: AuthUser = Depends(get_auth_user)) -> User:
    return auth_user.user


def _resolve_pat_auth(token: str, db: Session, request: Request | None = None) -> AuthUser:
    if not is_well_formed_pat(token):
        raise _unauthorized()

    token_hash = hash_token(token, get_settings().token_pepper)
    now = datetime.now(timezone.utc)

    stmt: Select[tuple[ApiToken, User]] = (
        select(ApiToken, User)
        .join(User, User.id == ApiToken.user_id)
        .where(
            ApiToken.token_hash == token_hash,
            ApiToken.revoked_at.is_(None),
            or_(ApiToken.expires_at.is_(None), ApiToken.expires_at > now),
        )
    )
    row = db.execute(stmt).first()
    if row is None:
        raise _unauthorized()

    token_obj, user = row
    token_obj.last_used_at = now
    db.add(token_obj)
    db.commit()
    db.refresh(token_obj)
    if request is not None:
        request.state.auth_user_id = str(user.id)

    return AuthUser(user=user, token=token_obj)


def _resolve_clerk_auth(token: str, db: Session, request: Request | None = None) -> AuthUser:
    claims: dict[str, Any] = verify_clerk_jwt(token=token, settings=get_settings())
    email_claim = claims.get("email")
    email = email_claim if isinstance(email_claim, str) else None
    identity = ClerkIdentity(clerk_user_id=str(claims["sub"]), email=email)
    user = get_or_create_user_for_clerk(identity=identity, db=db)
    if request is not None:
        request.state.auth_user_id = str(user.id)
    return AuthUser(user=user)


def get_or_create_user_for_clerk(identity: ClerkIdentity, db: Session) -> User:
    user = db.execute(select(User).where(User.clerk_user_id == identity.clerk_user_id)).scalar_one_or_none()
    if user:
        if identity.email and user.email != identity.email:
            user.email = identity.email
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    user = User(clerk_user_id=identity.clerk_user_id, email=identity.email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_clerk_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(creds)
    return _resolve_clerk_auth(token=token, db=db, request=request).user


def get_any_authenticated_user(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_bearer_token(creds)

    try:
        return _resolve_pat_auth(token, db, request=request).user
    except HTTPException:
        if not _looks_like_jwt(token):
            raise _unauthorized("Invalid PAT token.")

    try:
        return _resolve_clerk_auth(token=token, db=db, request=request).user
    except HTTPException as exc:
        if exc.status_code >= 500:
            raise
        raise _unauthorized("Invalid token. Provide a valid PAT or Clerk session token.") from exc


def ensure_thread_access(thread_id: UUID, user_id: UUID, db: Session) -> None:
    from app.db.models import XThread

    exists = db.execute(select(XThread.id).where(XThread.id == thread_id, XThread.user_id == user_id)).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
