from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Chunk, XThreadItem
from app.schemas.chat import ChatFilters, CitedSource
from app.services.openai_client import OpenAIServiceError, call_openai_json
from app.services.prompts import GROUNDED_ANALYSIS_PROMPT

BULL_HINTS = ("bull", "upside", "tailwind", "growth", "beat", "strong", "improve", "long")
BEAR_HINTS = ("bear", "downside", "risk", "bottleneck", "weak", "miss", "headwind", "short")
FORECAST_HINTS = ("will", "expect", "forecast", "guidance", "could", "target", "likely", "next quarter")
OPINION_HINTS = ("i think", "we think", "i believe", "opinion", "imo", "view")


@dataclass
class RetrievedChunk:
    chunk: Chunk
    distance: float


@dataclass
class AnswerBundle:
    answer_text: str
    cited_sources: list[CitedSource]


def _parse_date(value: Any) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _parse_datetime(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _passes_filters(metadata: dict[str, Any], filters: ChatFilters | None) -> bool:
    if not filters:
        return True

    if filters.author_handle:
        author = str(metadata.get("author_handle") or "").lower().lstrip("@")
        if author != filters.author_handle.lower().lstrip("@"):
            return False

    if filters.date_range:
        item_date = _parse_date(metadata.get("created_at"))
        if filters.date_range.start and item_date and item_date < filters.date_range.start:
            return False
        if filters.date_range.end and item_date and item_date > filters.date_range.end:
            return False

    return True


def retrieve_chunks(
    db: Session,
    *,
    user_id: UUID,
    query_vector: list[float],
    scope: str,
    thread_id: UUID | None,
    top_k: int,
    filters: ChatFilters | None,
) -> list[RetrievedChunk]:
    stmt = select(Chunk, Chunk.embedding.cosine_distance(query_vector).label("distance")).where(Chunk.user_id == user_id)

    if scope == "thread":
        if thread_id is None:
            return []

        thread_item_ids = select(XThreadItem.item_id).where(XThreadItem.thread_id == thread_id)
        stmt = stmt.where(
            or_(
                and_(Chunk.source_type == "x_thread", Chunk.source_id == thread_id),
                and_(Chunk.source_type == "x_item", Chunk.source_id.in_(thread_item_ids)),
            )
        )

    stmt = stmt.order_by("distance").limit(max(top_k * 4, 20))

    rows = db.execute(stmt).all()

    filtered: list[RetrievedChunk] = []
    for chunk, distance in rows:
        metadata = chunk.metadata_json or {}
        if _passes_filters(metadata, filters):
            filtered.append(RetrievedChunk(chunk=chunk, distance=float(distance)))
        if len(filtered) >= top_k:
            break

    return filtered


def _shorten(text: str, max_len: int = 240) -> str:
    stripped = " ".join((text or "").split())
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 3].rstrip() + "..."


def _dedupe_sources(chunks: list[RetrievedChunk]) -> list[CitedSource]:
    evidence = []
    for rc in chunks:
        metadata = rc.chunk.metadata_json or {}
        tweet_url = metadata.get("tweet_url")
        if not tweet_url:
            continue

        snippet = _shorten(rc.chunk.chunk_text)
        evidence.append(
            CitedSource(
                tweet_url=str(tweet_url),
                tweet_id=metadata.get("tweet_id"),
                author_handle=metadata.get("author_handle"),
                created_at=_parse_datetime(metadata.get("created_at")),
                snippet=snippet,
            )
        )

    deduped_sources: list[CitedSource] = []
    seen_urls: set[str] = set()
    for source in evidence:
        if source.tweet_url in seen_urls:
            continue
        seen_urls.add(source.tweet_url)
        deduped_sources.append(source)

    return deduped_sources[:8]


def _unknown_bundle(reason: str) -> AnswerBundle:
    answer = (
        "Facts: Unknown / Speculation.\n"
        "Opinions: Unknown / Speculation.\n"
        "Forecasts: Unknown / Speculation.\n"
        "Bull Case: Unknown / Speculation.\n"
        "Bear Case: Unknown / Speculation.\n"
        f"Uncertainties: {reason}"
    )
    return AnswerBundle(answer_text=answer, cited_sources=[])


def _classify_line(snippet: str) -> str:
    lowered = snippet.lower()
    if any(k in lowered for k in FORECAST_HINTS):
        return "forecast"
    if any(k in lowered for k in OPINION_HINTS):
        return "opinion"
    return "fact"


def _build_rule_based_answer(question: str, sources: list[CitedSource]) -> str:
    if not sources:
        return _unknown_bundle("No cited tweets matched this request.").answer_text

    facts: list[str] = []
    opinions: list[str] = []
    forecasts: list[str] = []
    bull_case: list[str] = []
    bear_case: list[str] = []

    for source in sources:
        line = f"{source.snippet} (source: {source.tweet_url})"
        classification = _classify_line(source.snippet)
        if classification == "forecast":
            forecasts.append(line)
        elif classification == "opinion":
            opinions.append(line)
        else:
            facts.append(line)

        lowered = source.snippet.lower()
        if any(k in lowered for k in BULL_HINTS):
            bull_case.append(line)
        if any(k in lowered for k in BEAR_HINTS):
            bear_case.append(line)

    if not facts:
        facts = ["Unknown / Speculation: no directly factual claims were retrieved."]
    if not opinions:
        opinions = ["Unknown / Speculation: no explicit opinion statements were retrieved."]
    if not forecasts:
        forecasts = ["Unknown / Speculation: no forward-looking statements were retrieved."]
    if not bull_case:
        bull_case = ["Unknown / Speculation: no clearly bullish evidence in cited tweets."]
    if not bear_case:
        bear_case = ["Unknown / Speculation: no clearly bearish evidence in cited tweets."]

    uncertainties = [
        "Unknown / Speculation: anything not explicitly stated in the cited tweets above.",
        f"Query asked: {question}",
    ]

    return "\n".join(
        [
            "Facts:",
            *[f"- {line}" for line in facts[:4]],
            "Opinions:",
            *[f"- {line}" for line in opinions[:4]],
            "Forecasts:",
            *[f"- {line}" for line in forecasts[:4]],
            "Bull Case:",
            *[f"- {line}" for line in bull_case[:4]],
            "Bear Case:",
            *[f"- {line}" for line in bear_case[:4]],
            "Uncertainties:",
            *[f"- {line}" for line in uncertainties],
        ]
    )


def _uses_local_chat_model(model: str) -> bool:
    return model.strip().lower().startswith("local-")


def _build_chat_user_prompt(question: str, sources: list[CitedSource]) -> str:
    source_lines: list[str] = []
    for idx, source in enumerate(sources, start=1):
        source_lines.append(
            "\n".join(
                [
                    f"[Source {idx}]",
                    f"tweet_url: {source.tweet_url}",
                    f"tweet_id: {source.tweet_id or 'unknown'}",
                    f"author_handle: {source.author_handle or 'unknown'}",
                    f"created_at: {source.created_at.isoformat() if source.created_at else 'unknown'}",
                    f"snippet: {source.snippet}",
                ]
            )
        )

    return "\n\n".join(
        [
            f"Question:\n{question}",
            "Retrieved sources:",
            "\n\n".join(source_lines),
            (
                "Return sections exactly in this order:\n"
                "Facts\nOpinions\nForecasts\nBull Case\nBear Case\nUncertainties\n\n"
                "For every material claim, include at least one explicit tweet URL from the sources."
            ),
        ]
    )


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OpenAIServiceError("OpenAI chat response missing choices.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise OpenAIServiceError("OpenAI chat response has invalid choice payload.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise OpenAIServiceError("OpenAI chat response missing message payload.")

    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content.strip()

    raise OpenAIServiceError("OpenAI chat response has empty message content.")


def _build_openai_answer(question: str, sources: list[CitedSource]) -> str:
    settings = get_settings()
    payload = {
        "model": settings.chat_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": GROUNDED_ANALYSIS_PROMPT},
            {"role": "user", "content": _build_chat_user_prompt(question, sources)},
        ],
    }
    response = call_openai_json("chat/completions", payload)
    return _extract_chat_completion_text(response)


def build_answer(question: str, chunks: list[RetrievedChunk]) -> AnswerBundle:
    deduped_sources = _dedupe_sources(chunks)
    if not deduped_sources:
        return _unknown_bundle("No cited tweets matched this request.")

    settings = get_settings()
    if _uses_local_chat_model(settings.chat_model):
        return AnswerBundle(answer_text=_build_rule_based_answer(question, deduped_sources), cited_sources=deduped_sources)

    answer = _build_openai_answer(question, deduped_sources)
    return AnswerBundle(answer_text=answer, cited_sources=deduped_sources)
