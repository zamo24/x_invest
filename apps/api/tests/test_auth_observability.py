from __future__ import annotations

from datetime import datetime, timedelta, timezone
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_token
from app.db.models import ApiToken, User
from app.db.session import SessionLocal


def _build_pat() -> str:
    return f"xic_pat_{uuid.uuid4().hex}{uuid.uuid4().hex}"


def test_health_returns_request_id_header(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200, response.text
    request_id = response.headers.get("x-request-id")
    assert request_id
    assert response.json()["request_id"] == request_id


def test_health_preserves_client_request_id(client: TestClient) -> None:
    request_id = "test-request-id-123"
    response = client.get("/health", headers={"x-request-id": request_id})
    assert response.status_code == 200, response.text
    assert response.headers.get("x-request-id") == request_id
    assert response.json()["request_id"] == request_id


def test_create_token_sets_default_expiry_and_enforces_max(
    client: TestClient,
    monkeypatch,
) -> None:
    clerk_sub = f"clerk_{uuid.uuid4().hex[:12]}"

    def fake_verify_clerk_jwt(token: str, settings) -> dict[str, str]:
        return {"sub": clerk_sub, "email": "clerk@example.com"}

    monkeypatch.setattr("app.api.deps.verify_clerk_jwt", fake_verify_clerk_jwt)
    headers = {"Authorization": "Bearer fake.jwt.token"}

    create = client.post(
        "/v1/tokens",
        headers=headers,
        json={"name": "Rotation Token"},
    )
    assert create.status_code == 200, create.text
    payload = create.json()
    assert payload["expires_at"] is not None

    expires_at = datetime.fromisoformat(payload["expires_at"].replace("Z", "+00:00"))
    delta_days = (expires_at - datetime.now(timezone.utc)).days
    assert 80 <= delta_days <= 91

    too_long = client.post(
        "/v1/tokens",
        headers=headers,
        json={"name": "Too Long", "expires_in_days": get_settings().pat_max_ttl_days + 1},
    )
    assert too_long.status_code == 422
    assert "cannot exceed" in too_long.text


def test_expired_pat_is_rejected(client: TestClient) -> None:
    settings = get_settings()
    pat = _build_pat()
    clerk_user_id = f"expired_{uuid.uuid4().hex[:12]}"

    with SessionLocal() as db:
        user = User(clerk_user_id=clerk_user_id, email="expired@example.com")
        db.add(user)
        db.flush()

        db.add(
            ApiToken(
                user_id=user.id,
                name="expired",
                token_hash=hash_token(pat, settings.token_pepper),
                token_fingerprint="xic_pat_xx...yy",
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )
        )
        db.commit()
        user_id = user.id

    response = client.get("/v1/library/items", headers={"Authorization": f"Bearer {pat}"})
    assert response.status_code == 401

    with SessionLocal() as db:
        db_user = db.execute(select(User).where(User.id == user_id)).scalar_one_or_none()
        if db_user:
            db.delete(db_user)
            db.commit()


def test_library_accepts_clerk_jwt_for_web_requests(client: TestClient, monkeypatch) -> None:
    clerk_sub = f"web_{uuid.uuid4().hex[:12]}"

    def fake_verify_clerk_jwt(token: str, settings) -> dict[str, str]:
        return {"sub": clerk_sub, "email": "web@example.com"}

    monkeypatch.setattr("app.api.deps.verify_clerk_jwt", fake_verify_clerk_jwt)
    response = client.get("/v1/library/items", headers={"Authorization": "Bearer web.jwt.token"})
    assert response.status_code == 200, response.text

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.clerk_user_id == clerk_sub)).scalar_one_or_none()
        if user:
            db.delete(user)
            db.commit()
