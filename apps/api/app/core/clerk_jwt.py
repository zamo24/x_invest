from __future__ import annotations

from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, status
from jwt import PyJWKClient
from jwt.exceptions import InvalidTokenError, PyJWKClientError

from app.core.config import Settings


def _clerk_unauthorized(detail: str = "Invalid Clerk session token") -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


@lru_cache(maxsize=8)
def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url)


def verify_clerk_jwt(token: str, settings: Settings) -> dict[str, Any]:
    if not settings.clerk_issuer or not settings.clerk_jwks_url:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Clerk JWT verification is not configured on the API.",
        )

    try:
        signing_key = _get_jwk_client(settings.clerk_jwks_url).get_signing_key_from_jwt(token)
        decode_kwargs: dict[str, Any] = {
            "key": signing_key.key,
            "algorithms": ["RS256"],
            "issuer": settings.clerk_issuer,
            "options": {"verify_aud": bool(settings.clerk_audience)},
            "leeway": settings.clerk_jwt_leeway_seconds,
        }
        if settings.clerk_audience:
            decode_kwargs["audience"] = settings.clerk_audience

        claims = jwt.decode(token, **decode_kwargs)
    except PyJWKClientError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to fetch Clerk signing keys.",
        ) from exc
    except InvalidTokenError as exc:
        raise _clerk_unauthorized() from exc

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise _clerk_unauthorized("Clerk session token missing subject claim.")

    return claims
