from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Iterable
from uuid import UUID

from app.db.models import XItem

STATUS_RE = re.compile(r"/status/(\d+)")
ARTICLE_RE = re.compile(r"/i/article/([A-Za-z0-9_-]+)")


def normalize_tweet_id(tweet_id: str | None, url: str, text: str) -> str:
    if tweet_id and tweet_id.strip():
        return tweet_id.strip()

    match = STATUS_RE.search(url or "")
    if match:
        return match.group(1)

    synthetic = hashlib.sha256(f"{url}|{text}".encode("utf-8")).hexdigest()[:20]
    return f"synthetic_{synthetic}"


def stable_item_hash(user_id: UUID, tweet_id: str, url: str, text: str) -> str:
    return hashlib.sha256(f"{user_id}:{tweet_id}:{url}:{text}".encode("utf-8")).hexdigest()


def normalize_article_id(article_id: str | None, url: str, title: str, text: str) -> str:
    if article_id and article_id.strip():
        return article_id.strip()

    match = ARTICLE_RE.search(url or "")
    if match:
        return match.group(1)

    synthetic = hashlib.sha256(f"{url}|{title}|{text}".encode("utf-8")).hexdigest()[:20]
    return f"synthetic_article_{synthetic}"


def build_item_chunk_text(item: XItem) -> str:
    source_kind = None
    title = None
    if isinstance(item.json_raw, dict):
        source_kind = item.json_raw.get("source_kind")
        title = item.json_raw.get("title")

    if source_kind == "article":
        lines = [
            "X Article",
            f"Title: {title or 'Untitled'}",
            f"URL: {item.url}",
            f"Author: @{item.author_handle}",
            item.text,
        ]
        return "\n".join(lines)

    lines = [
        f"Tweet by @{item.author_handle}",
        f"URL: {item.url}",
        item.text,
    ]
    if item.quoted_json:
        q = item.quoted_json
        q_author = q.get("author_handle") or "unknown"
        q_text = q.get("text") or ""
        lines.extend([f"Quoted tweet by @{q_author}", q_text])
    return "\n".join(lines)


def _split_text_chunks(text: str, *, max_chars: int, max_chunks: int) -> list[str]:
    normalized = (text or "").replace("\r\n", "\n").strip()
    if not normalized:
        return []

    paragraphs = [part.strip() for part in re.split(r"\n{2,}", normalized) if part.strip()]
    if not paragraphs:
        paragraphs = [normalized]

    chunks: list[str] = []
    current = ""

    def flush_current() -> None:
        nonlocal current
        if current and len(chunks) < max_chunks:
            chunks.append(current.strip())
            current = ""

    for paragraph in paragraphs:
        remaining = paragraph
        while remaining:
            if len(remaining) > max_chars:
                if current:
                    flush_current()
                piece = remaining[:max_chars]
                if len(chunks) < max_chunks:
                    chunks.append(piece.strip())
                remaining = remaining[max_chars:]
                continue

            candidate = f"{current}\n\n{remaining}".strip() if current else remaining
            if len(candidate) <= max_chars:
                current = candidate
                remaining = ""
            else:
                flush_current()

        if len(chunks) >= max_chunks:
            break

    flush_current()
    return chunks[:max_chunks]


def build_article_chunk_texts(
    item: XItem,
    *,
    max_body_chunk_chars: int = 1800,
    max_chunks: int = 200,
) -> list[str]:
    source_kind = None
    title = None
    if isinstance(item.json_raw, dict):
        source_kind = item.json_raw.get("source_kind")
        title = item.json_raw.get("title")

    if source_kind != "article":
        return [build_item_chunk_text(item)]

    body_chunks = _split_text_chunks(item.text, max_chars=max_body_chunk_chars, max_chunks=max_chunks)
    if not body_chunks:
        body_chunks = [""]

    total = len(body_chunks)
    header = "\n".join(
        [
            "X Article",
            f"Title: {title or 'Untitled'}",
            f"URL: {item.url}",
            f"Author: @{item.author_handle}",
        ]
    )

    return [f"{header}\nPart {idx + 1}/{total}\n{body}" for idx, body in enumerate(body_chunks)]


def build_thread_title(items: list[XItem], root_url: str | None) -> str:
    if items:
        first = items[0].text.strip().replace("\n", " ")
        return first[:120] if first else (root_url or "Saved X Thread")
    return root_url or "Saved X Thread"


def build_thread_macro_chunk_text(items: Iterable[XItem], max_chars: int = 6000) -> str:
    parts: list[str] = []
    total = 0
    for idx, item in enumerate(items, start=1):
        piece = f"[{idx}] @{item.author_handle} {item.url}\n{item.text.strip()}\n"
        if total + len(piece) > max_chars:
            break
        parts.append(piece)
        total += len(piece)
    return "\n".join(parts)


def coalesce_capture_time(captured_at: datetime | None) -> datetime:
    return captured_at or datetime.utcnow()
