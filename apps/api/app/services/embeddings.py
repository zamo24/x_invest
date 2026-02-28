from __future__ import annotations

import hashlib
import math
import re
from typing import Iterable

from app.db.models import EMBEDDING_DIM

TOKEN_RE = re.compile(r"[A-Za-z0-9_]+")


def _normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm <= 1e-12:
        return vec
    return [v / norm for v in vec]


def embed_text(text: str, dim: int = EMBEDDING_DIM) -> list[float]:
    vec = [0.0] * dim
    for token in TOKEN_RE.findall((text or "").lower()):
        digest = hashlib.sha256(token.encode("utf-8")).hexdigest()
        idx = int(digest[:8], 16) % dim
        sign = 1.0 if int(digest[8:10], 16) % 2 == 0 else -1.0
        weight = 1.0 + (int(digest[10:12], 16) / 255.0)
        vec[idx] += sign * weight
    return _normalize(vec)


def embed_many(texts: Iterable[str], dim: int = EMBEDDING_DIM) -> list[list[float]]:
    return [embed_text(text, dim=dim) for text in texts]
