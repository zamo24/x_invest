from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from app.core.config import get_settings
from app.db.models import EMBEDDING_DIM
from app.services.openai_client import OpenAIServiceError, call_openai_json

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return vec
    return [v / norm for v in vec]


def _local_embed_text(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    vec = [0.0] * dim
    for token in TOKEN_RE.findall((text or "").lower()):
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        weight = 1.0 + (int(digest[10:12], 16) / 255.0)
        vec[idx] += sign * weight
    return _normalize(vec)


def _uses_local_embeddings(model: str) -> bool:
    return model.strip().lower().startswith("local-")


def _openai_embed_many(texts: list[str], model: str, dim: int) -> list[list[float]]:
    payload: dict[str, object] = {"model": model, "input": texts}
    if model.startswith("text-embedding-3"):
        payload["dimensions"] = dim

    response = call_openai_json("embeddings", payload)
    data = response.get("data")
    if not isinstance(data, list):
        raise OpenAIServiceError("OpenAI embeddings response is missing 'data'.")

    sorted_rows = sorted(data, key=lambda row: int(row.get("index", 0)) if isinstance(row, dict) else 0)
    vectors: list[list[float]] = []

    for row in sorted_rows:
        if not isinstance(row, dict):
            raise OpenAIServiceError("OpenAI embeddings response contains invalid rows.")
        embedding = row.get("embedding")
        if not isinstance(embedding, list):
            raise OpenAIServiceError("OpenAI embeddings response row missing 'embedding'.")
        vector = [float(v) for v in embedding]
        if len(vector) != dim:
            raise OpenAIServiceError(
                f"Embedding dimension mismatch. Expected {dim}, received {len(vector)}. "
                f"Set EMBEDDING_DIM to match your model output."
            )
        vectors.append(vector)

    if len(vectors) != len(texts):
        raise OpenAIServiceError("OpenAI embeddings count mismatch.")

    return vectors


def embed_text(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    return embed_many([text], dim=dim)[0]


def embed_many(texts: Iterable[str], dim: int = EMBEDDING_DIM) -> list[list[float]]:
    text_list = list(texts)
    if not text_list:
        return []

    settings = get_settings()
    model = settings.embedding_model

    if _uses_local_embeddings(model):
        return [_local_embed_text(text, dim=dim) for text in text_list]

    return _openai_embed_many(text_list, model=model, dim=dim)
