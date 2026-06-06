from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import XThreadCapture
from app.db.session import SessionLocal


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload(root_tweet_id: str, text: str, *, include_reply: bool = False, is_partial: bool = False) -> dict:
    root_url = f"https://x.com/smoke/status/{root_tweet_id}"
    tweets = [
        {
            "tweet_id": root_tweet_id,
            "url": root_url,
            "author_handle": "smoke",
            "author_name": "Smoke Test",
            "created_at": _iso_now(),
            "text": text,
            "captured_at": _iso_now(),
        }
    ]
    if include_reply:
        tweets.append(
            {
                "tweet_id": f"{root_tweet_id}1",
                "url": f"https://x.com/smoke/status/{root_tweet_id}1",
                "author_handle": "smoke",
                "author_name": "Smoke Test",
                "created_at": _iso_now(),
                "text": "reply captured only in version one",
                "captured_at": _iso_now(),
            }
        )

    return {
        "capture_type": "thread",
        "page_url": root_url,
        "root_tweet_id": root_tweet_id,
        "root_tweet_url": root_url,
        "tweets": tweets,
        "captured_count": len(tweets),
        "is_partial": is_partial,
        "partial_reason": "Replies still loading" if is_partial else None,
    }


def test_recapturing_same_thread_bumps_version_instead_of_creating_duplicates(
    client: TestClient,
    auth_context: Any,
) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}
    root_tweet_id = f"pytest_{uuid4().hex[:14]}"

    first = client.post(
        "/v1/ingest/x",
        headers=headers,
        json=_payload(root_tweet_id, "first capture", include_reply=True),
    )
    assert first.status_code == 200, first.text
    first_json = first.json()
    assert first_json["thread_id"]
    assert first_json["thread_version"] == 1

    second = client.post(
        "/v1/ingest/x",
        headers=headers,
        json=_payload(root_tweet_id, "second capture", is_partial=True),
    )
    assert second.status_code == 200, second.text
    second_json = second.json()
    assert second_json["thread_id"] == first_json["thread_id"]
    assert second_json["thread_version"] == 2

    list_threads = client.get("/v1/library/threads", headers=headers)
    assert list_threads.status_code == 200, list_threads.text
    threads = [t for t in list_threads.json() if t["id"] == first_json["thread_id"]]
    assert len(threads) == 1
    assert threads[0]["capture_version"] == 2

    thread_detail = client.get(f"/v1/library/threads/{first_json['thread_id']}", headers=headers)
    assert thread_detail.status_code == 200, thread_detail.text
    latest = thread_detail.json()
    assert latest["selected_capture"]["capture_version"] == 2
    assert latest["selected_capture"]["is_partial"] is True
    assert [capture["capture_version"] for capture in latest["captures"]] == [2, 1]
    assert [item["text"] for item in latest["items"]] == ["second capture"]

    first_capture = client.get(f"/v1/library/threads/{first_json['thread_id']}?version=1", headers=headers)
    assert first_capture.status_code == 200, first_capture.text
    first_capture_json = first_capture.json()
    assert first_capture_json["selected_capture"]["capture_version"] == 1
    assert first_capture_json["selected_capture"]["is_partial"] is False
    assert [item["text"] for item in first_capture_json["items"]] == [
        "first capture",
        "reply captured only in version one",
    ]

    missing_capture = client.get(f"/v1/library/threads/{first_json['thread_id']}?version=99", headers=headers)
    assert missing_capture.status_code == 404, missing_capture.text

    with SessionLocal() as db:
        captures = db.execute(
            select(XThreadCapture)
            .where(XThreadCapture.thread_id == UUID(first_json["thread_id"]))
            .order_by(XThreadCapture.capture_version.asc())
        ).scalars().all()
        assert len(captures) == 2
        assert "first capture" in (captures[0].macro_chunk_text or "")
        assert "reply captured only in version one" in (captures[0].macro_chunk_text or "")
        assert "second capture" in (captures[1].macro_chunk_text or "")
