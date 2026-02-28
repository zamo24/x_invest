from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_token
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


def get_auth_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> AuthUser:
    if creds is None or creds.scheme.lower() != "bearer":
        raise _unauthorized()
    return _resolve_pat_auth(creds.credentials.strip(), db)


def get_current_user(auth_user: AuthUser = Depends(get_auth_user)) -> User:
    return auth_user.user


def _resolve_pat_auth(token: str, db: Session) -> AuthUser:
    token_hash = hash_token(token, get_settings().token_pepper)

    stmt: Select[tuple[ApiToken, User]] = (
        select(ApiToken, User)
        .join(User, User.id == ApiToken.user_id)
        .where(ApiToken.token_hash == token_hash, ApiToken.revoked_at.is_(None))
    )
    row = db.execute(stmt).first()
    if row is None:
        raise _unauthorized()

    token_obj, user = row
    token_obj.last_used_at = datetime.now(timezone.utc)
    db.add(token_obj)
    db.commit()
    db.refresh(token_obj)

    return AuthUser(user=user, token=token_obj)


def get_clerk_identity(
    x_clerk_user_id: str | None = Header(default=None),
    x_clerk_email: str | None = Header(default=None),
) -> ClerkIdentity:
    if not x_clerk_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing x-clerk-user-id header for web-authenticated endpoint.",
        )
    return ClerkIdentity(clerk_user_id=x_clerk_user_id, email=x_clerk_email)


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
    identity: ClerkIdentity = Depends(get_clerk_identity),
    db: Session = Depends(get_db),
) -> User:
    return get_or_create_user_for_clerk(identity=identity, db=db)


def get_any_authenticated_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    x_clerk_user_id: str | None = Header(default=None),
    x_clerk_email: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> User:
    if creds and creds.scheme.lower() == "bearer":
        return _resolve_pat_auth(creds.credentials.strip(), db).user

    if x_clerk_user_id:
        identity = ClerkIdentity(clerk_user_id=x_clerk_user_id, email=x_clerk_email)
        return get_or_create_user_for_clerk(identity=identity, db=db)

    raise _unauthorized("Missing authentication. Provide Bearer PAT or x-clerk-user-id.")


def ensure_thread_access(thread_id: UUID, user_id: UUID, db: Session) -> None:
    from app.db.models import XThread

    exists = db.execute(select(XThread.id).where(XThread.id == thread_id, XThread.user_id == user_id)).scalar_one_or_none()
    if exists is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found")
