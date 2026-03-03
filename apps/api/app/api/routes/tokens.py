from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_clerk_user
from app.core.config import get_settings
from app.core.security import create_plaintext_token, fingerprint_token, hash_token
from app.db.models import ApiToken, User
from app.db.session import get_db
from app.schemas.tokens import TokenCreateRequest, TokenCreateResponse, TokenListItem, TokenRevokeResponse

router = APIRouter()


@router.post("/tokens", response_model=TokenCreateResponse)
def create_token(
    payload: TokenCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_clerk_user),
) -> TokenCreateResponse:
    plaintext = create_plaintext_token()
    settings = get_settings()
    pepper = settings.token_pepper
    ttl_days = payload.expires_in_days or settings.pat_default_ttl_days
    if ttl_days > settings.pat_max_ttl_days:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"expires_in_days cannot exceed {settings.pat_max_ttl_days}",
        )
    expires_at = datetime.now(timezone.utc) + timedelta(days=ttl_days)

    token = ApiToken(
        user_id=user.id,
        name=payload.name,
        token_hash=hash_token(plaintext, pepper),
        token_fingerprint=fingerprint_token(plaintext),
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()
    db.refresh(token)

    return TokenCreateResponse(
        id=token.id,
        name=token.name,
        token=plaintext,
        token_fingerprint=token.token_fingerprint,
        created_at=token.created_at,
        expires_at=token.expires_at,
    )


@router.get("/tokens", response_model=list[TokenListItem])
def list_tokens(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_clerk_user),
) -> list[TokenListItem]:
    stmt = (
        select(ApiToken)
        .where(ApiToken.user_id == user.id)
        .order_by(ApiToken.created_at.desc())
    )
    tokens = db.execute(stmt).scalars().all()
    return [TokenListItem.model_validate(token) for token in tokens]


@router.delete("/tokens/{token_id}", response_model=TokenRevokeResponse)
def revoke_token(
    token_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_clerk_user),
) -> TokenRevokeResponse:
    token = db.execute(
        select(ApiToken).where(ApiToken.id == token_id, ApiToken.user_id == user.id)
    ).scalar_one_or_none()
    if token is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")

    now = datetime.now(timezone.utc)
    token.revoked_at = now
    db.add(token)
    db.commit()

    return TokenRevokeResponse(id=token.id, revoked_at=now)
