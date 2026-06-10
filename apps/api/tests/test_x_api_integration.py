from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import x_integration as routes
from app.core.config import Settings
from app.db.models import (
    ChatMessage,
    ChatThread,
    XApiUsage,
    XBookmarkFolderMapping,
    XIntegration,
    XItem,
    XOAuthState,
    XThreadCapture,
)
from app.db.session import SessionLocal
from app.services.x_api import XApiClient, XBudgetExceeded, XPage, build_authorization_url
from app.services.x_crypto import decrypt_x_secret, encrypt_x_secret
from app.services.x_ingestion import parse_x_post_id, revalidate_user_sources


def _headers(auth_context: Any) -> dict[str, str]:
    return {"Authorization": f"Bearer {auth_context.pat}"}


def _post(post_id: str, *, text: str = "Official API post", author_id: str = "author-1") -> dict[str, Any]:
    return {
        "id": post_id,
        "text": text,
        "author_id": author_id,
        "created_at": "2026-06-10T12:00:00Z",
        "conversation_id": post_id,
        "edit_history_tweet_ids": [post_id],
    }


def _page(*posts: dict[str, Any]) -> XPage:
    return XPage(
        posts=list(posts),
        includes={"users": [{"id": "author-1", "name": "Official Author", "username": "official"}]},
    )


def _connect(auth_context: Any) -> None:
    with SessionLocal() as db:
        db.add(
            XIntegration(
                user_id=UUID(auth_context.user_id),
                x_user_id="x-user",
                x_username="connected",
                access_token_encrypted=encrypt_x_secret("access-token"),
                refresh_token_encrypted=encrypt_x_secret("refresh-token"),
                access_token_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                granted_scopes=["tweet.read", "users.read", "bookmark.read", "offline.access"],
            )
        )
        db.commit()


class FakeClient:
    def __init__(self, pages: list[XPage]) -> None:
        self.pages = pages

    def get_post(self, post_id: str) -> XPage:
        return self.pages[0]

    def search_conversation(self, conversation_id: str, *, next_token: str | None = None) -> XPage:
        return self.pages[-1]

    def get_bookmarks(self, *, pagination_token: str | None = None, max_results: int = 100) -> XPage:
        return self.pages[0]

    def get_bookmark_folders(self) -> list[dict[str, Any]]:
        return []

    def get_posts(self, post_ids: list[str]) -> XPage:
        return self.pages[0]


def test_oauth_authorization_url_pkce_and_encryption(client: TestClient, auth_context: Any) -> None:
    response = client.post("/v1/integrations/x/authorize", headers=_headers(auth_context))
    assert response.status_code == 200, response.text
    url = response.json()["authorization_url"]
    assert "code_challenge_method=S256" in url
    assert "tweet.read+users.read+bookmark.read+offline.access" in url
    assert "bookmark.write" not in url and "tweet.write" not in url
    assert build_authorization_url(state="state", code_challenge="challenge").startswith("https://x.com/i/oauth2/authorize?")

    encrypted = encrypt_x_secret("secret-token")
    assert encrypted != "secret-token"
    assert decrypt_x_secret(encrypted) == "secret-token"


def test_oauth_state_is_single_use(client: TestClient, auth_context: Any, monkeypatch: Any) -> None:
    authorize = client.post("/v1/integrations/x/authorize", headers=_headers(auth_context)).json()
    state = authorize["authorization_url"].split("state=")[1].split("&")[0]
    monkeypatch.setattr(
        routes,
        "exchange_authorization_code",
        lambda **_: {"access_token": "access", "refresh_token": "refresh", "expires_in": 7200, "scope": "tweet.read users.read bookmark.read offline.access"},
    )
    monkeypatch.setattr(routes.XApiClient, "get_me", lambda self: {"id": "x-user", "username": "official"})
    first = client.get("/v1/integrations/x/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert first.status_code == 302
    second = client.get("/v1/integrations/x/callback", params={"code": "code", "state": state}, follow_redirects=False)
    assert second.status_code == 400


def test_expired_oauth_state_is_rejected(client: TestClient, auth_context: Any) -> None:
    with SessionLocal() as db:
        db.add(
            XOAuthState(
                user_id=UUID(auth_context.user_id),
                state_hash=routes._hash("expired"),
                pkce_verifier_encrypted=encrypt_x_secret("verifier"),
                expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
            )
        )
        db.commit()
    response = client.get("/v1/integrations/x/callback", params={"code": "code", "state": "expired"})
    assert response.status_code == 400


def test_post_url_parsing_and_official_ingestion(client: TestClient, auth_context: Any, monkeypatch: Any) -> None:
    _connect(auth_context)
    post_id = str(uuid4().int)[:18]
    assert parse_x_post_id(f"https://x.com/official/status/{post_id}") == post_id
    monkeypatch.setattr(routes, "get_x_client", lambda **_: FakeClient([_page(_post(post_id))]))
    response = client.post(
        "/v1/sources/x",
        headers=_headers(auth_context),
        json={"url": f"https://x.com/official/status/{post_id}", "folder_id": None, "mode": "post"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["created"] == 1
    with SessionLocal() as db:
        item = db.execute(select(XItem).where(XItem.user_id == UUID(auth_context.user_id), XItem.tweet_id == post_id)).scalar_one()
        assert item.content_status == "active"
        assert item.json_raw["external_source"] == "x_api"


def test_author_thread_excludes_other_users_and_preserves_capture(client: TestClient, auth_context: Any, monkeypatch: Any) -> None:
    _connect(auth_context)
    root_id = str(uuid4().int)[:18]
    reply_id = str(uuid4().int)[:18]
    unrelated_id = str(uuid4().int)[:18]
    selected = _page(_post(root_id))
    conversation = _page(
        _post(root_id),
        {
            **_post(reply_id),
            "conversation_id": root_id,
            "in_reply_to_user_id": "author-1",
            "referenced_tweets": [{"type": "replied_to", "id": root_id}],
        },
        _post(unrelated_id, author_id="other"),
    )
    monkeypatch.setattr(routes, "get_x_client", lambda **_: FakeClient([selected, conversation]))
    response = client.post(
        "/v1/sources/x",
        headers=_headers(auth_context),
        json={"url": f"https://x.com/official/status/{root_id}", "mode": "author_thread"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_partial"] is True
    with SessionLocal() as db:
        captures = db.execute(select(XThreadCapture).where(XThreadCapture.user_id == UUID(auth_context.user_id))).scalars().all()
        assert len(captures) == 1
        assert reply_id in (captures[0].macro_chunk_text or "")
        assert unrelated_id not in (captures[0].macro_chunk_text or "")


def test_unsupported_article_is_link_only_and_missing_connection_is_actionable(client: TestClient, auth_context: Any) -> None:
    _connect(auth_context)
    article = client.post(
        "/v1/sources/x",
        headers=_headers(auth_context),
        json={"url": "https://x.com/i/article/abc", "mode": "post"},
    )
    assert article.status_code == 200
    with SessionLocal() as db:
        item = db.execute(select(XItem).where(XItem.id == UUID(article.json()["item_ids"][0]))).scalar_one()
        assert item.content_status == "unsupported"
        assert item.json_raw["capture_mode"] == "link_only"
        assert "unsupported" in item.text.lower()
    disconnected = client.delete("/v1/integrations/x", headers=_headers(auth_context))
    assert disconnected.status_code == 200
    missing = client.post(
        "/v1/sources/x",
        headers=_headers(auth_context),
        json={"url": "https://x.com/official/status/123", "mode": "post"},
    )
    assert missing.status_code == 409


def test_budget_error_is_normalized() -> None:
    assert XBudgetExceeded().code == "budget_exhausted"


def test_bookmark_sync_paginates_and_maps_folders(client: TestClient, auth_context: Any, monkeypatch: Any) -> None:
    _connect(auth_context)
    first_id = str(uuid4().int)[:18]
    second_id = str(uuid4().int)[:18]

    class BookmarkClient(FakeClient):
        def get_bookmarks(self, *, pagination_token: str | None = None, max_results: int = 100) -> XPage:
            return XPage(
                posts=[_post(second_id)] if pagination_token else [_post(first_id)],
                includes=_page(_post(first_id)).includes,
                next_token=None if pagination_token else "next",
            )

        def get_bookmark_folders(self) -> list[dict[str, Any]]:
            return [{"id": "folder-x", "name": "Semiconductors"}]

        def get_bookmark_folder_posts(self, folder_id: str, *, pagination_token: str | None = None) -> XPage:
            return _page(_post(first_id))

    monkeypatch.setattr(routes, "get_x_client", lambda **_: BookmarkClient([]))
    response = client.post("/v1/integrations/x/bookmarks/sync", headers=_headers(auth_context))
    assert response.status_code == 200, response.text
    assert response.json()["fetched"] == 2
    assert response.json()["folders_mapped"] == 1
    with SessionLocal() as db:
        mapping = db.execute(
            select(XBookmarkFolderMapping).where(XBookmarkFolderMapping.user_id == UUID(auth_context.user_id))
        ).scalar_one()
        assert mapping.x_folder_id == "folder-x"


def test_revalidation_updates_current_content_but_preserves_snapshot_and_citation(
    client: TestClient, auth_context: Any, monkeypatch: Any
) -> None:
    _connect(auth_context)
    post_id = str(uuid4().int)[:18]
    monkeypatch.setattr(routes, "get_x_client", lambda **_: FakeClient([_page(_post(post_id, text="Original text"))]))
    saved = client.post(
        "/v1/sources/x",
        headers=_headers(auth_context),
        json={"url": f"https://x.com/official/status/{post_id}", "mode": "author_thread"},
    )
    assert saved.status_code == 200, saved.text
    with SessionLocal() as db:
        thread = ChatThread(user_id=UUID(auth_context.user_id), title="Persisted citation")
        db.add(thread)
        db.flush()
        db.add(
            ChatMessage(
                thread_id=thread.id,
                user_id=UUID(auth_context.user_id),
                role="assistant",
                message_text="Cited answer",
                cited_sources_json=[{"tweet_url": f"https://x.com/official/status/{post_id}", "snippet": "Original text"}],
            )
        )
        db.commit()

        user = routes._integration(db, UUID(auth_context.user_id)).user
        result = revalidate_user_sources(
            db=db,
            user=user,
            client=FakeClient([_page(_post(post_id, text="Modified text"))]),
        )
        assert result["updated"] == 1
        item = db.execute(select(XItem).where(XItem.user_id == user.id, XItem.tweet_id == post_id)).scalar_one()
        capture = db.execute(select(XThreadCapture).where(XThreadCapture.user_id == user.id)).scalar_one()
        message = db.execute(select(ChatMessage).where(ChatMessage.user_id == user.id)).scalar_one()
        assert item.text == "Modified text"
        assert "Original text" in (capture.macro_chunk_text or "")
        assert message.cited_sources_json[0]["snippet"] == "Original text"


def test_usage_budget_enforcement(auth_context: Any) -> None:
    _connect(auth_context)
    with SessionLocal() as db:
        integration = db.execute(
            select(XIntegration).where(XIntegration.user_id == UUID(auth_context.user_id))
        ).scalar_one()
        db.add(XApiUsage(user_id=integration.user_id, operation="test", requested_post_count=1, returned_post_count=1))
        db.commit()
        client = XApiClient(
            db=db,
            user_id=integration.user_id,
            integration=integration,
            settings=Settings(X_MONTHLY_POST_READ_BUDGET=1, X_TOKEN_ENCRYPTION_KEY="test-key"),
        )
        try:
            client._enforce_budget(1)
        except XBudgetExceeded:
            pass
        else:
            raise AssertionError("Expected XBudgetExceeded")
