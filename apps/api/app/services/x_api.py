from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import XApiUsage, XIntegration
from app.services.x_crypto import decrypt_x_secret, encrypt_x_secret

X_SCOPES = ("tweet.read", "users.read", "bookmark.read", "offline.access")
POST_FIELDS = "id,text,author_id,created_at,conversation_id,in_reply_to_user_id,referenced_tweets,edit_history_tweet_ids"
EXPANSIONS = "author_id,referenced_tweets.id,referenced_tweets.id.author_id"
USER_FIELDS = "id,name,username"


class XApiError(RuntimeError):
    def __init__(self, message: str, *, code: str = "x_api_error", status_code: int = 502) -> None:
        super().__init__(message)
        self.code = code
        self.status_code = status_code


class XBudgetExceeded(XApiError):
    def __init__(self) -> None:
        super().__init__("The configured monthly X post-read budget has been exhausted.", code="budget_exhausted", status_code=429)


@dataclass
class XPage:
    posts: list[dict[str, Any]]
    includes: dict[str, Any]
    next_token: str | None = None


def build_authorization_url(*, state: str, code_challenge: str, settings: Settings | None = None) -> str:
    resolved = settings or get_settings()
    if not resolved.x_client_id:
        raise XApiError("X_CLIENT_ID is not configured.", code="not_configured", status_code=503)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": resolved.x_client_id,
            "redirect_uri": resolved.x_redirect_uri,
            "scope": " ".join(X_SCOPES),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
    )
    return f"https://x.com/i/oauth2/authorize?{query}"


def exchange_authorization_code(*, code: str, code_verifier: str, settings: Settings | None = None) -> dict[str, Any]:
    resolved = settings or get_settings()
    return _token_request(
        {
            "code": code,
            "grant_type": "authorization_code",
            "client_id": resolved.x_client_id or "",
            "redirect_uri": resolved.x_redirect_uri,
            "code_verifier": code_verifier,
        },
        settings=resolved,
    )


def _token_request(data: dict[str, str], *, settings: Settings) -> dict[str, Any]:
    auth = (settings.x_client_id, settings.x_client_secret) if settings.x_client_secret and settings.x_client_id else None
    request_data = dict(data)
    if auth:
        request_data.pop("client_id", None)
    try:
        response = httpx.post(
            f"{settings.x_api_base_url.rstrip('/')}/2/oauth2/token",
            data=request_data,
            auth=auth,
            timeout=20,
        )
    except httpx.HTTPError as exc:
        raise XApiError(f"X OAuth request failed: {exc}", code="oauth_network_error") from exc
    if response.is_error:
        raise _error_from_response(response)
    payload = response.json()
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise XApiError("X OAuth response did not include an access token.", code="oauth_invalid_response")
    return payload


def _error_from_response(response: httpx.Response) -> XApiError:
    try:
        payload = response.json()
    except ValueError:
        payload = {}
    detail = payload.get("detail") or payload.get("title") or payload.get("error_description") or "X API request failed."
    if response.status_code == 429:
        return XApiError(str(detail), code="rate_limited", status_code=429)
    if response.status_code in {401, 403}:
        return XApiError(str(detail), code="not_authorized", status_code=response.status_code)
    if response.status_code == 404:
        return XApiError(str(detail), code="not_found", status_code=404)
    return XApiError(str(detail), status_code=502)


class XApiClient:
    def __init__(self, *, db: Session, user_id: UUID, integration: XIntegration, settings: Settings | None = None) -> None:
        self.db = db
        self.user_id = user_id
        self.integration = integration
        self.settings = settings or get_settings()

    def _monthly_reads(self) -> int:
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return int(
            self.db.execute(
                select(func.coalesce(func.sum(XApiUsage.returned_post_count), 0)).where(
                    XApiUsage.user_id == self.user_id, XApiUsage.created_at >= start
                )
            ).scalar_one()
        )

    def _enforce_budget(self, requested: int) -> None:
        budget = self.settings.x_monthly_post_read_budget
        if budget > 0 and self._monthly_reads() + requested > budget:
            raise XBudgetExceeded()

    def _access_token(self) -> str:
        now = datetime.now(timezone.utc)
        expires = self.integration.access_token_expires_at
        if expires and (expires.tzinfo is None and expires.replace(tzinfo=timezone.utc) <= now + timedelta(seconds=60) or expires.tzinfo and expires <= now + timedelta(seconds=60)):
            self.refresh_access_token()
        return decrypt_x_secret(self.integration.access_token_encrypted)

    def refresh_access_token(self) -> None:
        if not self.integration.refresh_token_encrypted:
            self.integration.status = "reauthorization_required"
            self.db.commit()
            raise XApiError("X connection must be authorized again.", code="reauthorization_required", status_code=401)
        payload = _token_request(
            {
                "refresh_token": decrypt_x_secret(self.integration.refresh_token_encrypted),
                "grant_type": "refresh_token",
                "client_id": self.settings.x_client_id or "",
            },
            settings=self.settings,
        )
        self.integration.access_token_encrypted = encrypt_x_secret(str(payload["access_token"]))
        if payload.get("refresh_token"):
            self.integration.refresh_token_encrypted = encrypt_x_secret(str(payload["refresh_token"]))
        self.integration.access_token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 7200)))
        self.integration.granted_scopes = str(payload.get("scope") or " ".join(X_SCOPES)).split()
        self.integration.status = "connected"
        self.db.add(self.integration)
        self.db.commit()

    def _get(
        self,
        path: str,
        *,
        params: dict[str, Any],
        operation: str,
        requested_posts: int = 0,
        count_returned_posts: bool = True,
    ) -> dict[str, Any]:
        self._enforce_budget(requested_posts)
        try:
            response = httpx.get(
                f"{self.settings.x_api_base_url.rstrip('/')}{path}",
                params=params,
                headers={"Authorization": f"Bearer {self._access_token()}"},
                timeout=30,
            )
        except httpx.HTTPError as exc:
            raise XApiError(f"X API request failed: {exc}", code="network_error") from exc
        if response.is_error:
            raise _error_from_response(response)
        payload = response.json()
        returned = 0
        if count_returned_posts:
            returned = len(payload.get("data") or []) if isinstance(payload.get("data"), list) else int(bool(payload.get("data")))
        self.db.add(
            XApiUsage(
                user_id=self.user_id,
                operation=operation,
                requested_post_count=requested_posts,
                returned_post_count=returned,
                metadata_json={"path": path},
            )
        )
        self.db.commit()
        return payload

    def get_me(self) -> dict[str, Any]:
        payload = self._get(
            "/2/users/me",
            params={"user.fields": USER_FIELDS},
            operation="users.me",
            count_returned_posts=False,
        )
        return dict(payload.get("data") or {})

    def get_post(self, post_id: str) -> XPage:
        payload = self._get(
            f"/2/tweets/{post_id}",
            params={"tweet.fields": POST_FIELDS, "expansions": EXPANSIONS, "user.fields": USER_FIELDS},
            operation="posts.lookup.one",
            requested_posts=1,
        )
        data = payload.get("data")
        return XPage(posts=[data] if isinstance(data, dict) else [], includes=dict(payload.get("includes") or {}))

    def get_posts(self, post_ids: list[str]) -> XPage:
        if not post_ids or len(post_ids) > 100:
            raise ValueError("Batch post lookup requires 1 to 100 post IDs.")
        payload = self._get(
            "/2/tweets",
            params={"ids": ",".join(post_ids), "tweet.fields": POST_FIELDS, "expansions": EXPANSIONS, "user.fields": USER_FIELDS},
            operation="posts.lookup.batch",
            requested_posts=len(post_ids),
        )
        return XPage(posts=list(payload.get("data") or []), includes=dict(payload.get("includes") or {}))

    def get_bookmarks(self, *, pagination_token: str | None = None, max_results: int = 100) -> XPage:
        params: dict[str, Any] = {
            "max_results": min(max(max_results, 1), 100),
            "tweet.fields": POST_FIELDS,
            "expansions": EXPANSIONS,
            "user.fields": USER_FIELDS,
        }
        if pagination_token:
            params["pagination_token"] = pagination_token
        payload = self._get(
            f"/2/users/{self.integration.x_user_id}/bookmarks",
            params=params,
            operation="bookmarks.list",
            requested_posts=params["max_results"],
        )
        return XPage(
            posts=list(payload.get("data") or []),
            includes=dict(payload.get("includes") or {}),
            next_token=(payload.get("meta") or {}).get("next_token"),
        )

    def get_bookmark_folders(self) -> list[dict[str, Any]]:
        payload = self._get(
            f"/2/users/{self.integration.x_user_id}/bookmarks/folders",
            params={},
            operation="bookmarks.folders",
            count_returned_posts=False,
        )
        return list(payload.get("data") or [])

    def get_bookmark_folder_posts(self, folder_id: str, *, pagination_token: str | None = None) -> XPage:
        params: dict[str, Any] = {
            "max_results": 100,
            "tweet.fields": POST_FIELDS,
            "expansions": EXPANSIONS,
            "user.fields": USER_FIELDS,
        }
        if pagination_token:
            params["pagination_token"] = pagination_token
        payload = self._get(
            f"/2/users/{self.integration.x_user_id}/bookmarks/folders/{folder_id}",
            params=params,
            operation="bookmarks.folder.posts",
            requested_posts=100,
        )
        return XPage(
            posts=list(payload.get("data") or []),
            includes=dict(payload.get("includes") or {}),
            next_token=(payload.get("meta") or {}).get("next_token"),
        )

    def search_conversation(self, conversation_id: str, *, next_token: str | None = None) -> XPage:
        params: dict[str, Any] = {
            "query": f"conversation_id:{conversation_id}",
            "max_results": 100,
            "tweet.fields": POST_FIELDS,
            "expansions": EXPANSIONS,
            "user.fields": USER_FIELDS,
        }
        if next_token:
            params["next_token"] = next_token
        payload = self._get("/2/tweets/search/recent", params=params, operation="posts.search.conversation", requested_posts=100)
        return XPage(
            posts=list(payload.get("data") or []),
            includes=dict(payload.get("includes") or {}),
            next_token=(payload.get("meta") or {}).get("next_token"),
        )


def get_x_client(*, db: Session, user_id: UUID, integration: XIntegration) -> XApiClient:
    return XApiClient(db=db, user_id=user_id, integration=integration)
