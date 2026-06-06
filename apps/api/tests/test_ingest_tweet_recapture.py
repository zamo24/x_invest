from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes import ingest as ingest_route
from app.db.models import Chunk, XItem
from app.db.session import SessionLocal


def _iso_at(hour: int) -> str:
    return datetime(2026, 3, 2, hour, tzinfo=timezone.utc).isoformat()


def _payload(
    tweet_id: str,
    *,
    text: str,
    author_handle: str = "recapture",
    author_name: str | None = "Recapture Tester",
    created_at: str | None = None,
    captured_at: str | None = None,
    quoted_text: str = "Original quoted thesis.",
    json_raw: dict[str, Any] | None = None,
) -> dict[str, Any]:
    tweet_url = f"https://x.com/{author_handle}/status/{tweet_id}"
    return {
        "capture_type": "tweet",
        "page_url": tweet_url,
        "root_tweet_id": tweet_id,
        "root_tweet_url": tweet_url,
        "tweets": [
            {
                "tweet_id": tweet_id,
                "url": tweet_url,
                "author_handle": author_handle,
                "author_name": author_name,
                "created_at": created_at or _iso_at(10),
                "text": text,
                "quoted": {
                    "tweet_id": f"quoted_{tweet_id}",
                    "url": f"https://x.com/quoted/status/{tweet_id}",
                    "text": quoted_text,
                    "author_handle": "quoted",
                    "author_name": "Quoted Author",
                    "created_at": _iso_at(9),
                },
                "captured_at": captured_at or _iso_at(11),
                "json_raw": json_raw,
            }
        ],
        "captured_count": 1,
        "is_partial": False,
    }


def _load_item_and_chunk(item_id: str) -> tuple[XItem, Chunk]:
    with SessionLocal() as db:
        item = db.execute(select(XItem).where(XItem.id == UUID(item_id))).scalar_one()
        chunk = db.execute(
            select(Chunk).where(
                Chunk.source_type == "x_item",
                Chunk.source_id == item.id,
                Chunk.chunk_order == 0,
            )
        ).scalar_one()
        db.expunge(item)
        db.expunge(chunk)
        return item, chunk


def test_changed_tweet_recapture_refreshes_item_and_chunk(
    client: TestClient,
    auth_context: Any,
    monkeypatch: Any,
) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}
    tweet_id = f"pytest_recapture_{uuid4().hex[:12]}"

    first = client.post(
        "/v1/ingest/x",
        headers=headers,
        json=_payload(tweet_id, text="Original HBM thesis.", json_raw={"version": 1}),
    )
    assert first.status_code == 200, first.text
    item_id = first.json()["item_ids"][0]
    original_item, original_chunk = _load_item_and_chunk(item_id)

    original_embed_text = ingest_route.embed_text
    embedded_texts: list[str] = []

    def tracking_embed_text(text: str) -> list[float]:
        embedded_texts.append(text)
        return original_embed_text(text)

    monkeypatch.setattr(ingest_route, "embed_text", tracking_embed_text)

    second = client.post(
        "/v1/ingest/x",
        headers=headers,
        json=_payload(
            tweet_id,
            text="Updated HBM thesis with stronger demand.",
            author_handle="recapture_updated",
            author_name="Updated Author",
            created_at=_iso_at(12),
            captured_at=_iso_at(13),
            quoted_text="Updated quoted thesis.",
            json_raw={"version": 2},
        ),
    )
    assert second.status_code == 200, second.text
    assert second.json()["item_ids"] == [item_id]
    assert second.json()["stored_count"] == 0
    assert len(embedded_texts) == 1

    updated_item, updated_chunk = _load_item_and_chunk(item_id)
    assert updated_item.author_handle == "recapture_updated"
    assert updated_item.author_name == "Updated Author"
    assert updated_item.text == "Updated HBM thesis with stronger demand."
    assert updated_item.quoted_json["text"] == "Updated quoted thesis."
    assert updated_item.json_raw == {"version": 2}
    assert updated_item.created_at == datetime(2026, 3, 2, 12, tzinfo=timezone.utc)
    assert updated_item.captured_at == datetime(2026, 3, 2, 13, tzinfo=timezone.utc)
    assert updated_item.hash != original_item.hash

    assert updated_chunk.id == original_chunk.id
    assert updated_chunk.chunk_text == embedded_texts[0]
    assert "Updated HBM thesis with stronger demand." in updated_chunk.chunk_text
    assert "Updated quoted thesis." in updated_chunk.chunk_text
    assert "Original HBM thesis." not in updated_chunk.chunk_text
    assert updated_chunk.metadata_json["author_handle"] == "recapture_updated"
    assert updated_chunk.metadata_json["created_at"] == _iso_at(12)


def test_metadata_only_tweet_recapture_skips_reembedding(
    client: TestClient,
    auth_context: Any,
    monkeypatch: Any,
) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}
    tweet_id = f"pytest_metadata_{uuid4().hex[:12]}"
    text = "HBM thesis content is unchanged."

    first = client.post(
        "/v1/ingest/x",
        headers=headers,
        json=_payload(tweet_id, text=text, json_raw={"capture": "first"}),
    )
    assert first.status_code == 200, first.text
    item_id = first.json()["item_ids"][0]
    original_item, original_chunk = _load_item_and_chunk(item_id)

    embedded_texts: list[str] = []

    def tracking_embed_text(text_to_embed: str) -> list[float]:
        embedded_texts.append(text_to_embed)
        return [0.0] * 256

    monkeypatch.setattr(ingest_route, "embed_text", tracking_embed_text)

    second = client.post(
        "/v1/ingest/x",
        headers=headers,
        json=_payload(
            tweet_id,
            text=text,
            author_name="Refreshed Display Name",
            created_at=_iso_at(14),
            captured_at=_iso_at(15),
            json_raw={"capture": "second"},
        ),
    )
    assert second.status_code == 200, second.text
    assert second.json()["item_ids"] == [item_id]
    assert second.json()["stored_count"] == 0
    assert embedded_texts == []

    updated_item, updated_chunk = _load_item_and_chunk(item_id)
    assert updated_item.author_name == "Refreshed Display Name"
    assert updated_item.json_raw == {"capture": "second"}
    assert updated_item.created_at == datetime(2026, 3, 2, 14, tzinfo=timezone.utc)
    assert updated_item.captured_at == datetime(2026, 3, 2, 15, tzinfo=timezone.utc)
    assert updated_item.hash == original_item.hash

    assert updated_chunk.id == original_chunk.id
    assert updated_chunk.chunk_text == original_chunk.chunk_text
    assert updated_chunk.metadata_json["created_at"] == _iso_at(14)
