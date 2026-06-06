from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _payload(root_tweet_id: str, text: str) -> dict:
    root_url = f"https://x.com/smoke/status/{root_tweet_id}"
    return {
        "capture_type": "thread",
        "page_url": root_url,
        "root_tweet_id": root_tweet_id,
        "root_tweet_url": root_url,
        "tweets": [
            {
                "tweet_id": root_tweet_id,
                "url": root_url,
                "author_handle": "smoke",
                "author_name": "Smoke Test",
                "created_at": _iso_now(),
                "text": text,
                "captured_at": _iso_now(),
            }
        ],
        "captured_count": 1,
        "is_partial": False,
    }


def test_recapturing_same_thread_bumps_version_instead_of_creating_duplicates(
    client: TestClient,
    auth_context: Any,
) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}
    root_tweet_id = f"pytest_{uuid4().hex[:14]}"

    first = client.post("/v1/ingest/x", headers=headers, json=_payload(root_tweet_id, "first capture"))
    assert first.status_code == 200, first.text
    first_json = first.json()
    assert first_json["thread_id"]
    assert first_json["thread_version"] == 1

    second = client.post("/v1/ingest/x", headers=headers, json=_payload(root_tweet_id, "second capture"))
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
    assert thread_detail.json()["items"][0]["text"] == "second capture"
