from __future__ import annotations

import os
import uuid
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import fingerprint_token, hash_token
from app.db.models import ApiToken, User
from app.db.session import SessionLocal


@pytest.fixture(scope="session", autouse=True)
def configure_test_models() -> None:
    os.environ["EMBEDDING_MODEL"] = "local-hash-v1"
    os.environ["CHAT_MODEL"] = "local-grounded-v1"
    get_settings.cache_clear()


@pytest.fixture()
def client() -> TestClient:
    from app.main import app

    with TestClient(app) as test_client:
        yield test_client


@dataclass
class AuthContext:
    user_id: str
    clerk_user_id: str
    pat: str


@pytest.fixture()
def auth_context() -> AuthContext:
    settings = get_settings()
    clerk_user_id = f"pytest_{uuid.uuid4().hex[:12]}"
    pat = f"xic_pat_pytest_{uuid.uuid4().hex}{uuid.uuid4().hex}"

    with SessionLocal() as db:
        user = User(clerk_user_id=clerk_user_id, email=f"{clerk_user_id}@example.com")
        db.add(user)
        db.flush()

        db.add(
            ApiToken(
                user_id=user.id,
                name="pytest-token",
                token_hash=hash_token(pat, settings.token_pepper),
                token_fingerprint=fingerprint_token(pat),
            )
        )
        db.commit()
        created_user_id = str(user.id)

    try:
        yield AuthContext(user_id=created_user_id, clerk_user_id=clerk_user_id, pat=pat)
    finally:
        with SessionLocal() as db:
            user = db.execute(select(User).where(User.clerk_user_id == clerk_user_id)).scalar_one_or_none()
            if user:
                db.delete(user)
                db.commit()
