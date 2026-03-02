from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.models import Chunk
from app.db.session import SessionLocal


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_article_ingest_and_library_listing(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}
    article_id = f"pytest_article_{uuid4().hex[:12]}"
    article_url = f"https://x.com/i/article/{article_id}"

    payload = {
        "capture_type": "article",
        "page_url": article_url,
        "article": {
            "article_id": article_id,
            "url": article_url,
            "title": "HBM Supply Outlook",
            "author_handle": "semicapital",
            "author_name": "Semi Capital",
            "created_at": _iso_now(),
            "text": "HBM packaging constraints are easing slowly in 2026.",
            "captured_at": _iso_now(),
        },
        "tweets": [],
        "captured_count": 1,
        "is_partial": False,
    }

    ingest = client.post("/v1/ingest/x", headers=headers, json=payload)
    assert ingest.status_code == 200, ingest.text
    ingest_json = ingest.json()
    assert ingest_json["stored_count"] == 1
    assert ingest_json["thread_id"] is None
    assert len(ingest_json["item_ids"]) == 1

    items = client.get("/v1/library/items", headers=headers)
    assert items.status_code == 200, items.text
    saved = next((item for item in items.json() if item["tweet_id"] == article_id), None)
    assert saved is not None
    assert saved["source_kind"] == "article"
    assert saved["title"] == "HBM Supply Outlook"


def test_long_article_creates_multiple_chunks(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}
    article_id = f"pytest_article_long_{uuid4().hex[:10]}"
    article_url = f"https://x.com/i/article/{article_id}"
    long_cjk = "".join(chr(0x4E00 + (idx % 2000)) for idx in range(24000))

    payload = {
        "capture_type": "article",
        "page_url": article_url,
        "article": {
            "article_id": article_id,
            "url": article_url,
            "title": "Long Article",
            "author_handle": "longform",
            "author_name": "Long Form",
            "created_at": _iso_now(),
            "text": long_cjk,
            "captured_at": _iso_now(),
        },
        "tweets": [],
        "captured_count": 1,
        "is_partial": False,
    }

    ingest = client.post("/v1/ingest/x", headers=headers, json=payload)
    assert ingest.status_code == 200, ingest.text
    item_id = UUID(ingest.json()["item_ids"][0])

    with SessionLocal() as db:
        chunk_count = db.execute(
            select(func.count())
            .select_from(Chunk)
            .where(Chunk.source_type == "x_item", Chunk.source_id == item_id)
        ).scalar_one()

    assert chunk_count > 1
