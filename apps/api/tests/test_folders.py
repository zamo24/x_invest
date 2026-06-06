from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi.testclient import TestClient


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_folder_create_assign_and_filter_flow(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}

    create = client.post("/v1/library/folders", headers=headers, json={"name": "HBM"})
    assert create.status_code == 200, create.text
    folder = create.json()
    folder_id = folder["id"]

    duplicate = client.post("/v1/library/folders", headers=headers, json={"name": "hbm"})
    assert duplicate.status_code == 409, duplicate.text

    root_tweet_id = f"pytest_folder_{uuid4().hex[:12]}"
    root_url = f"https://x.com/folder/status/{root_tweet_id}"
    ingest_payload = {
        "capture_type": "thread",
        "page_url": root_url,
        "root_tweet_id": root_tweet_id,
        "root_tweet_url": root_url,
        "folder_id": folder_id,
        "tweets": [
            {
                "tweet_id": root_tweet_id,
                "url": root_url,
                "author_handle": "foldertester",
                "author_name": "Folder Tester",
                "created_at": _iso_now(),
                "text": "HBM and photonics notes.",
                "captured_at": _iso_now(),
            }
        ],
        "captured_count": 1,
        "is_partial": False,
    }

    ingest = client.post("/v1/ingest/x", headers=headers, json=ingest_payload)
    assert ingest.status_code == 200, ingest.text
    ingest_json = ingest.json()
    thread_id = ingest_json["thread_id"]
    item_id = ingest_json["item_ids"][0]

    threads_in_folder = client.get(f"/v1/library/threads?folder_id={folder_id}", headers=headers)
    assert threads_in_folder.status_code == 200, threads_in_folder.text
    folder_threads = threads_in_folder.json()
    assert len(folder_threads) == 1
    assert folder_threads[0]["id"] == thread_id
    assert folder_threads[0]["folder_name"] == "HBM"

    items_in_folder = client.get(f"/v1/library/items?folder_id={folder_id}", headers=headers)
    assert items_in_folder.status_code == 200, items_in_folder.text
    assert len(items_in_folder.json()) == 1
    assert items_in_folder.json()[0]["id"] == item_id

    searched_items = client.get("/v1/library/items?q=photonics", headers=headers)
    assert searched_items.status_code == 200, searched_items.text
    assert any(item["id"] == item_id for item in searched_items.json())

    searched_threads = client.get("/v1/library/threads?q=photonics&author_handle=foldertester", headers=headers)
    assert searched_threads.status_code == 200, searched_threads.text
    assert any(thread["id"] == thread_id for thread in searched_threads.json())

    missing_items = client.get("/v1/library/items?q=not-a-real-thesis", headers=headers)
    assert missing_items.status_code == 200, missing_items.text
    assert all(item["id"] != item_id for item in missing_items.json())

    clear_thread_folder = client.patch(f"/v1/library/threads/{thread_id}/folder", headers=headers, json={"folder_id": None})
    assert clear_thread_folder.status_code == 200, clear_thread_folder.text
    assert clear_thread_folder.json()["folder_id"] is None

    unassigned_threads = client.get("/v1/library/threads?unassigned=true", headers=headers)
    assert unassigned_threads.status_code == 200, unassigned_threads.text
    assert any(thread["id"] == thread_id for thread in unassigned_threads.json())

    clear_item_folder = client.patch(f"/v1/library/items/{item_id}/folder", headers=headers, json={"folder_id": None})
    assert clear_item_folder.status_code == 200, clear_item_folder.text
    assert clear_item_folder.json()["folder_id"] is None
