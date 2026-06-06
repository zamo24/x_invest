from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import json
import re
from typing import Any
from uuid import UUID

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import Chunk, XItem, XThread, XThreadItem
from app.schemas.chat import ChatFilters, CitedSource
from app.services.openai_client import OpenAIServiceError, call_openai_json
from app.services.prompts import INVESTOR_COPILOT_PROMPT

WORD_RE = re.compile(r"[a-z0-9]{3,}")
URL_RE = re.compile(r"https?://[^\s)\],]+")
STOPWORDS = {
    "about",
    "after",
    "all",
    "and",
    "are",
    "but",
    "can",
    "for",
    "from",
    "has",
    "have",
    "into",
    "not",
    "over",
    "still",
    "the",
    "this",
    "what",
    "with",
    "your",
}


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


def _query_terms(text: str) -> set[str]:
    return {term for term in WORD_RE.findall((text or "").lower()) if term not in STOPWORDS}


def _lexical_score(query_terms: set[str], text: str) -> float:
    if not query_terms:
        return 0.0

    text_terms = set(WORD_RE.findall((text or "").lower()))
    if not text_terms:
        return 0.0

    overlap = len(query_terms & text_terms)
    return overlap / max(1, len(query_terms))


def _recency_score(metadata: dict[str, Any], *, now: datetime) -> float:
    created_at = _parse_datetime(metadata.get("created_at"))
    if created_at is None:
        return 0.0

    age_days = max(0.0, (now - created_at).total_seconds() / 86400.0)
    return max(0.0, 1.0 - (age_days / 365.0))


def _vector_score(distance: float) -> float:
    bounded_distance = min(max(distance, 0.0), 2.0)
    return 1.0 - (bounded_distance / 2.0)


def rerank_retrieved_chunks(
    candidates: list[RetrievedChunk],
    *,
    query_text: str,
    top_k: int,
    lexical_weight: float,
    recency_weight: float,
    now: datetime | None = None,
) -> list[RetrievedChunk]:
    query_terms = _query_terms(query_text)
    scored_at = now or datetime.now(timezone.utc)
    safe_lexical_weight = min(max(lexical_weight, 0.0), 0.8)
    safe_recency_weight = min(max(recency_weight, 0.0), 0.5)
    vector_weight = max(0.0, 1.0 - safe_lexical_weight - safe_recency_weight)

    def score(candidate: RetrievedChunk) -> tuple[float, float]:
        metadata = candidate.chunk.metadata_json or {}
        hybrid_score = (
            vector_weight * _vector_score(candidate.distance)
            + safe_lexical_weight * _lexical_score(query_terms, candidate.chunk.chunk_text)
            + safe_recency_weight * _recency_score(metadata, now=scored_at)
        )
        return (hybrid_score, -candidate.distance)

    return sorted(candidates, key=score, reverse=True)[:top_k]


def retrieve_chunks(
    db: Session,
    *,
    user_id: UUID,
    query_text: str,
    query_vector: list[float],
    scope: str,
    thread_id: UUID | None,
    top_k: int,
    filters: ChatFilters | None,
) -> list[RetrievedChunk]:
    stmt = select(Chunk, Chunk.embedding.cosine_distance(query_vector).label("distance")).where(Chunk.user_id == user_id)

    folder_id = filters.folder_id if filters else None
    if folder_id is not None:
        folder_item_ids = select(XItem.id).where(XItem.user_id == user_id, XItem.folder_id == folder_id)
        folder_thread_ids = select(XThread.id).where(XThread.user_id == user_id, XThread.folder_id == folder_id)
        stmt = stmt.where(
            or_(
                and_(Chunk.source_type == "x_item", Chunk.source_id.in_(folder_item_ids)),
                and_(Chunk.source_type == "x_thread", Chunk.source_id.in_(folder_thread_ids)),
            )
        )

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

    settings = get_settings()
    candidate_limit = max(
        top_k * max(1, settings.retrieval_oversample_multiplier),
        max(top_k, settings.retrieval_min_candidates),
    )
    stmt = stmt.order_by("distance").limit(candidate_limit)

    rows = db.execute(stmt).all()

    filtered: list[RetrievedChunk] = []
    for chunk, distance in rows:
        metadata = chunk.metadata_json or {}
        if _passes_filters(metadata, filters):
            filtered.append(RetrievedChunk(chunk=chunk, distance=float(distance)))

    return rerank_retrieved_chunks(
        filtered,
        query_text=query_text,
        top_k=top_k,
        lexical_weight=settings.retrieval_lexical_weight,
        recency_weight=settings.retrieval_recency_weight,
    )


def _shorten(text: str, max_len: int = 420) -> str:
    stripped = " ".join((text or "").split())
    if len(stripped) <= max_len:
        return stripped
    return stripped[: max_len - 3].rstrip() + "..."


def _dedupe_sources(chunks: list[RetrievedChunk]) -> list[CitedSource]:
    evidence_by_url: dict[str, dict[str, Any]] = {}
    for rc in chunks:
        metadata = rc.chunk.metadata_json or {}
        tweet_url = metadata.get("tweet_url")
        if not tweet_url:
            continue

        normalized_url = str(tweet_url)
        snippet = _shorten(rc.chunk.chunk_text)
        payload = evidence_by_url.setdefault(
            normalized_url,
            {
                "tweet_id": metadata.get("tweet_id"),
                "author_handle": metadata.get("author_handle"),
                "created_at": _parse_datetime(metadata.get("created_at")),
                "snippets": [],
            },
        )

        snippets: list[str] = payload["snippets"]
        if snippet and snippet not in snippets and len(snippets) < 4:
            snippets.append(snippet)

    deduped_sources: list[CitedSource] = []
    for tweet_url, payload in evidence_by_url.items():
        snippets = payload.get("snippets", [])
        merged_snippet = "\n---\n".join(snippets[:4]).strip()
        if not merged_snippet:
            merged_snippet = "No textual snippet available."

        source = CitedSource(
            tweet_url=tweet_url,
            tweet_id=payload.get("tweet_id"),
            author_handle=payload.get("author_handle"),
            created_at=payload.get("created_at"),
            snippet=merged_snippet,
        )
        deduped_sources.append(source)

    return deduped_sources[:8]


def _is_casual_prompt(question: str) -> bool:
    normalized_question = " ".join(question.lower().split()).rstrip("!?.")
    return normalized_question in {
        "good afternoon",
        "good evening",
        "good morning",
        "hello",
        "hey",
        "hey there",
        "hi",
        "hi there",
        "how are you",
        "thanks",
        "thank you",
        "what can you do",
        "who are you",
    }


def _build_local_answer(question: str, sources: list[CitedSource]) -> str:
    if _is_casual_prompt(question):
        return (
            "I'm your Investor Copilot. I can discuss investing ideas, explain concepts, "
            "and analyze the X sources you save. What would you like to talk through?"
        )

    if not sources:
        return (
            "I don't have enough relevant evidence in your saved X sources to answer that confidently. "
            "I can still help you frame the question or identify what evidence would resolve it."
        )

    evidence_lines = [f"- {_shorten(source.snippet, 320)} (source: {source.tweet_url})" for source in sources[:4]]
    return "\n\n".join(
        [
            "Based on the relevant items in your saved X library, here is the evidence I found:",
            "\n".join(evidence_lines),
            "That is what the saved evidence directly supports; drawing a broader conclusion would require more context.",
        ]
    )


def _build_local_answer_bundle(question: str, sources: list[CitedSource]) -> AnswerBundle:
    used_sources = [] if _is_casual_prompt(question) else sources[:4]
    return AnswerBundle(answer_text=_build_local_answer(question, used_sources), cited_sources=used_sources)


def _uses_local_chat_model(model: str) -> bool:
    return model.strip().lower().startswith("local-")


def _build_chat_user_prompt_with_history(
    question: str,
    sources: list[CitedSource],
    *,
    history: list[tuple[str, str]],
) -> str:
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

    history_block = "No prior messages."
    if history:
        history_lines: list[str] = []
        for role, text in history[-8:]:
            role_label = "User" if role == "user" else "Assistant"
            history_lines.append(f"{role_label}: {text.strip()}")
        history_block = "\n".join(history_lines)

    return "\n\n".join(
        [
            "Conversation context (recent turns):",
            history_block,
            f"Current question:\n{question}",
            "Retrieved sources:",
            "\n\n".join(source_lines) if source_lines else "No relevant saved X sources were retrieved.",
            (
                "Return ONLY valid JSON. No markdown, no code fences, no prose outside JSON.\n"
                "Schema:\n"
                "{\n"
                '  "answer": string,\n'
                '  "grounded_claims": [{"claim": string, "citations": [tweet_url, ...]}]\n'
                "}\n\n"
                "Rules:\n"
                "- Write `answer` as a natural response to the user. Use paragraphs, bullets, or headings only when useful.\n"
                "- Do not force a fixed format or include a sources section; sources are displayed separately.\n"
                "- Cite only URLs from retrieved sources in `grounded_claims`.\n"
                "- Every source-based claim must appear verbatim in `answer` and in `grounded_claims`.\n"
                "- If no saved source supports the requested analysis, say that naturally instead of inventing an answer.\n"
                "- For casual conversation or stable educational explanations, `grounded_claims` may be empty."
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


def _normalize_url(value: str) -> str:
    return value.strip().rstrip(".,;:)")


def _parse_llm_conversational_payload(content: str) -> tuple[str, list[dict[str, Any]]] | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    answer_raw = parsed.get("answer")
    claims_raw = parsed.get("grounded_claims")
    if not isinstance(answer_raw, str) or not answer_raw.strip() or not isinstance(claims_raw, list):
        return None

    claims: list[dict[str, Any]] = []
    for item in claims_raw:
        if not isinstance(item, dict):
            return None

        claim_raw = item.get("claim")
        citations_raw = item.get("citations")
        if not isinstance(claim_raw, str) or not claim_raw.strip() or not isinstance(citations_raw, list):
            return None

        citations: list[str] = []
        for citation in citations_raw:
            if not isinstance(citation, str) or not citation.strip():
                return None
            citations.append(_normalize_url(citation))

        claims.append({"claim": claim_raw.strip(), "citations": citations})

    return answer_raw.strip(), claims


def _has_claim_source_overlap(claim: str, snippet: str) -> bool:
    claim_clean = claim.strip().lower()
    snippet_clean = snippet.strip().lower()
    if not claim_clean or not snippet_clean:
        return False
    if claim_clean in snippet_clean or snippet_clean in claim_clean:
        return True

    claim_tokens = set(WORD_RE.findall(claim_clean))
    snippet_tokens = set(WORD_RE.findall(snippet_clean))
    if not claim_tokens or not snippet_tokens:
        return False

    overlap_size = len(claim_tokens & snippet_tokens)
    if len(claim_tokens) <= 4:
        return overlap_size >= 1
    return overlap_size >= 2


def _validate_conversational_answer(
    answer: str,
    claims: list[dict[str, Any]],
    sources: list[CitedSource],
) -> tuple[str, list[CitedSource]] | None:
    source_by_url = {_normalize_url(source.tweet_url): source for source in sources}
    answer_lower = answer.lower()
    used_urls: set[str] = set()

    for entry in claims:
        claim = entry["claim"]
        citations = entry["citations"]
        if claim.lower() not in answer_lower or not citations:
            return None

        if any(citation not in source_by_url for citation in citations):
            return None

        if not all(_has_claim_source_overlap(claim=claim, snippet=source_by_url[citation].snippet) for citation in citations):
            return None

        used_urls.update(citations)

    for answer_url in URL_RE.findall(answer):
        normalized_url = _normalize_url(answer_url)
        if ("x.com/" in normalized_url or "twitter.com/" in normalized_url) and normalized_url not in source_by_url:
            return None
        if normalized_url in source_by_url and normalized_url not in used_urls:
            return None

    validated_sources = [source for source in sources if _normalize_url(source.tweet_url) in used_urls]
    return answer, validated_sources


def _build_openai_answer(
    question: str,
    sources: list[CitedSource],
    *,
    chat_model: str,
    reasoning_effort: str | None,
    api_key: str | None,
    history: list[tuple[str, str]],
) -> str:
    payload: dict[str, Any] = {
        "model": chat_model,
        "messages": [
            {"role": "system", "content": INVESTOR_COPILOT_PROMPT},
            {"role": "user", "content": _build_chat_user_prompt_with_history(question, sources, history=history)},
        ],
    }
    # Some newer model families (e.g. gpt-5*) only allow default temperature.
    if not chat_model.strip().lower().startswith("gpt-5"):
        payload["temperature"] = 0.1
    elif reasoning_effort and reasoning_effort != "none":
        payload["reasoning_effort"] = reasoning_effort
    response = call_openai_json("chat/completions", payload, api_key=api_key)
    return _extract_chat_completion_text(response)


def build_answer(
    question: str,
    chunks: list[RetrievedChunk],
    *,
    chat_model: str | None = None,
    reasoning_effort: str | None = None,
    api_key: str | None = None,
    history: list[tuple[str, str]] | None = None,
) -> AnswerBundle:
    deduped_sources = _dedupe_sources(chunks)
    settings = get_settings()
    resolved_model = chat_model or settings.chat_model
    if _uses_local_chat_model(resolved_model):
        return _build_local_answer_bundle(question, deduped_sources)

    raw_answer = _build_openai_answer(
        question,
        deduped_sources,
        chat_model=resolved_model,
        reasoning_effort=reasoning_effort,
        api_key=api_key,
        history=history or [],
    )
    parsed = _parse_llm_conversational_payload(raw_answer)
    if parsed is None:
        return _build_local_answer_bundle(question, deduped_sources)

    validated = _validate_conversational_answer(parsed[0], parsed[1], deduped_sources)
    if validated is None:
        return _build_local_answer_bundle(question, deduped_sources)

    return AnswerBundle(answer_text=validated[0], cited_sources=validated[1])
