from __future__ import annotations

import hashlib
import re
from datetime import datetime
from typing import Iterable
from uuid import UUID

from app.db.models import XItem

STATUS_RE = re.compile(r"/status/(\d+)")


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


def build_item_chunk_text(item: XItem) -> str:
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
