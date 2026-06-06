from __future__ import annotations

import uuid
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import fingerprint_token, hash_token
from app.db.models import ApiToken, User
from app.db.session import SessionLocal


def _create_pat_for_user(*, clerk_user_id: str, email: str) -> tuple[str, str]:
    settings = get_settings()
    pat = f"xic_pat_{uuid.uuid4().hex}{uuid.uuid4().hex}"

    with SessionLocal() as db:
        user = User(clerk_user_id=clerk_user_id, email=email)
        db.add(user)
        db.flush()
        user_id = str(user.id)

        db.add(
            ApiToken(
                user_id=user.id,
                name="pytest-secondary-token",
                token_hash=hash_token(pat, settings.token_pepper),
                token_fingerprint=fingerprint_token(pat),
            )
        )
        db.commit()

    return pat, user_id


def _delete_user_by_id(user_id: str) -> None:
    with SessionLocal() as db:
        user = db.execute(select(User).where(User.id == uuid.UUID(user_id))).scalar_one_or_none()
        if user:
            db.delete(user)
            db.commit()


def test_chat_creates_and_persists_thread_history(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}

    first = client.post(
        "/v1/chat",
        headers=headers,
        json={"message": "First question", "scope": "all", "top_k": 4},
    )
    assert first.status_code == 200, first.text
    first_payload = first.json()
    chat_thread_id = first_payload["chat_thread_id"]
    assert chat_thread_id

    second = client.post(
        "/v1/chat",
        headers=headers,
        json={
            "message": "Follow-up question",
            "scope": "all",
            "top_k": 4,
            "chat_thread_id": chat_thread_id,
        },
    )
    assert second.status_code == 200, second.text
    assert second.json()["chat_thread_id"] == chat_thread_id

    threads_response = client.get("/v1/chat/threads", headers=headers)
    assert threads_response.status_code == 200, threads_response.text
    threads = threads_response.json()
    matching = [thread for thread in threads if thread["id"] == chat_thread_id]
    assert len(matching) == 1
    assert matching[0]["message_count"] == 4

    detail = client.get(f"/v1/chat/threads/{chat_thread_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    messages = detail.json()["messages"]
    assert len(messages) == 4
    assert [message["role"] for message in messages] == ["user", "assistant", "user", "assistant"]
    assert messages[0]["message_text"] == "First question"
    assert messages[2]["message_text"] == "Follow-up question"


def test_local_chat_uses_conversational_fallback(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}

    response = client.post(
        "/v1/chat",
        headers=headers,
        json={"message": "Hi", "scope": "all", "top_k": 4},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["answer_text"].startswith("I'm your Investor Copilot.")
    assert "Executive Summary" not in payload["answer_text"]
    assert payload["cited_sources"] == []


def test_chat_thread_endpoints_enforce_user_ownership(client: TestClient, auth_context: Any) -> None:
    owner_headers = {"Authorization": f"Bearer {auth_context.pat}"}

    created = client.post(
        "/v1/chat",
        headers=owner_headers,
        json={"message": "Owner thread", "scope": "all", "top_k": 4},
    )
    assert created.status_code == 200, created.text
    chat_thread_id = created.json()["chat_thread_id"]
    assert chat_thread_id

    other_clerk = f"pytest_other_{uuid.uuid4().hex[:12]}"
    other_pat, other_user_id = _create_pat_for_user(clerk_user_id=other_clerk, email=f"{other_clerk}@example.com")
    other_headers = {"Authorization": f"Bearer {other_pat}"}

    try:
        detail = client.get(f"/v1/chat/threads/{chat_thread_id}", headers=other_headers)
        assert detail.status_code == 404

        follow_up = client.post(
            "/v1/chat",
            headers=other_headers,
            json={
                "message": "Hijack thread",
                "scope": "all",
                "top_k": 4,
                "chat_thread_id": chat_thread_id,
            },
        )
        assert follow_up.status_code == 404

        rename = client.patch(
            f"/v1/chat/threads/{chat_thread_id}",
            headers=other_headers,
            json={"title": "Not allowed"},
        )
        assert rename.status_code == 404

        delete = client.delete(f"/v1/chat/threads/{chat_thread_id}", headers=other_headers)
        assert delete.status_code == 404
    finally:
        _delete_user_by_id(other_user_id)


def test_chat_thread_rename_and_delete(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}

    created = client.post(
        "/v1/chat",
        headers=headers,
        json={"message": "Rename me", "scope": "all", "top_k": 4},
    )
    assert created.status_code == 200, created.text
    chat_thread_id = created.json()["chat_thread_id"]
    assert chat_thread_id

    renamed = client.patch(
        f"/v1/chat/threads/{chat_thread_id}",
        headers=headers,
        json={"title": "HBM Thesis Thread"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["title"] == "HBM Thesis Thread"

    detail = client.get(f"/v1/chat/threads/{chat_thread_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    assert detail.json()["thread"]["title"] == "HBM Thesis Thread"

    deleted = client.delete(f"/v1/chat/threads/{chat_thread_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    missing = client.get(f"/v1/chat/threads/{chat_thread_id}", headers=headers)
    assert missing.status_code == 404


def test_chat_thread_pagination(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}
    created_ids: list[str] = []
    for idx in range(3):
        created = client.post(
            "/v1/chat",
            headers=headers,
            json={"message": f"Pagination thread {idx}", "scope": "all", "top_k": 4},
        )
        assert created.status_code == 200, created.text
        created_ids.append(created.json()["chat_thread_id"])

    first_page = client.get("/v1/chat/threads?limit=2&offset=0", headers=headers)
    assert first_page.status_code == 200, first_page.text
    first_page_threads = first_page.json()
    assert len(first_page_threads) == 2

    second_page = client.get("/v1/chat/threads?limit=2&offset=2", headers=headers)
    assert second_page.status_code == 200, second_page.text
    second_page_threads = second_page.json()
    assert len(second_page_threads) >= 1

    returned_ids = {thread["id"] for thread in first_page_threads + second_page_threads}
    assert set(created_ids).issubset(returned_ids)
