from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.services.rag import RetrievedChunk, rerank_retrieved_chunks


def _candidate(text: str, *, distance: float, created_at: datetime | None = None) -> RetrievedChunk:
    metadata = {}
    if created_at is not None:
        metadata["created_at"] = created_at.isoformat()
    chunk = SimpleNamespace(chunk_text=text, metadata_json=metadata)
    return RetrievedChunk(chunk=chunk, distance=distance)  # type: ignore[arg-type]


def test_hybrid_rerank_promotes_lexical_matches_when_vector_scores_are_close() -> None:
    now = datetime(2026, 3, 2, tzinfo=timezone.utc)
    generic = _candidate("Semicap equipment order commentary.", distance=0.10, created_at=now)
    lexical_match = _candidate("HBM supply remains constrained by packaging capacity.", distance=0.14, created_at=now)

    ranked = rerank_retrieved_chunks(
        [generic, lexical_match],
        query_text="HBM supply packaging",
        top_k=2,
        lexical_weight=0.25,
        recency_weight=0.0,
        now=now,
    )

    assert ranked[0] is lexical_match


def test_hybrid_rerank_uses_recency_as_tiebreaker() -> None:
    now = datetime(2026, 3, 2, tzinfo=timezone.utc)
    older = _candidate("HBM supply remains constrained.", distance=0.12, created_at=now - timedelta(days=300))
    newer = _candidate("HBM supply remains constrained.", distance=0.12, created_at=now - timedelta(days=2))

    ranked = rerank_retrieved_chunks(
        [older, newer],
        query_text="HBM supply",
        top_k=2,
        lexical_weight=0.2,
        recency_weight=0.1,
        now=now,
    )

    assert ranked[0] is newer
