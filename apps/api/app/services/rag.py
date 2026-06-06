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
from app.services.prompts import GROUNDED_ANALYSIS_PROMPT

BULL_HINTS = ("bull", "upside", "tailwind", "growth", "beat", "strong", "improve", "long")
BEAR_HINTS = ("bear", "downside", "risk", "bottleneck", "weak", "miss", "headwind", "short")
FORECAST_HINTS = ("will", "expect", "forecast", "guidance", "could", "target", "likely", "next quarter")
OPINION_HINTS = ("i think", "we think", "i believe", "opinion", "imo", "view")
SECTION_ORDER: list[tuple[str, str]] = [
    ("executive_summary", "Executive Summary"),
    ("facts", "Facts"),
    ("opinions", "Opinions"),
    ("forecasts", "Forecasts"),
    ("bull_case", "Bull Case"),
    ("bear_case", "Bear Case"),
    ("uncertainties", "Uncertainties"),
]
WORD_RE = re.compile(r"[a-z0-9]{3,}")
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


def _unknown_bundle(reason: str) -> AnswerBundle:
    answer = "\n\n".join(
        [
            "Executive Summary: Unknown / Speculation: insufficient grounded evidence to answer the question.",
            "Facts: Unknown / Speculation.",
            "Opinions: Unknown / Speculation.",
            "Forecasts: Unknown / Speculation.",
            "Bull Case: Unknown / Speculation.",
            "Bear Case: Unknown / Speculation.",
            f"Uncertainties: {reason}",
        ]
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
        "Unknown / Speculation: anything not explicitly stated in the cited sources above.",
        f"Unknown / Speculation: query context not fully covered -> {question}",
    ]

    def _as_section(title: str, lines: list[str], limit: int = 3) -> str:
        return f"{title}: {' '.join(lines[:limit])}"

    return "\n\n".join(
        [
            _as_section("Executive Summary", facts[:1] or ["Unknown / Speculation."]),
            _as_section("Facts", facts, 3),
            _as_section("Opinions", opinions, 2),
            _as_section("Forecasts", forecasts, 2),
            _as_section("Bull Case", bull_case, 2),
            _as_section("Bear Case", bear_case, 2),
            _as_section("Uncertainties", uncertainties, 2),
        ]
    )


def _uses_local_chat_model(model: str) -> bool:
    return model.strip().lower().startswith("local-")


def _build_chat_user_prompt(question: str, sources: list[CitedSource]) -> str:
    return _build_chat_user_prompt_with_history(question, sources, history=[])


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
            "\n\n".join(source_lines),
            (
                "Return ONLY valid JSON. No markdown, no code fences, no prose outside JSON.\n"
                "Schema:\n"
                "{\n"
                '  "executive_summary": [{"claim": string, "citations": [tweet_url, ...]}],\n'
                '  "facts": [{"claim": string, "citations": [tweet_url, ...]}],\n'
                '  "opinions": [{"claim": string, "citations": [tweet_url, ...]}],\n'
                '  "forecasts": [{"claim": string, "citations": [tweet_url, ...]}],\n'
                '  "bull_case": [{"claim": string, "citations": [tweet_url, ...]}],\n'
                '  "bear_case": [{"claim": string, "citations": [tweet_url, ...]}],\n'
                '  "uncertainties": [{"claim": string, "citations": [tweet_url, ...]}]\n'
                "}\n\n"
                "Rules:\n"
                "- Cite only URLs from retrieved sources.\n"
                "- Unsupported claims must start with 'Unknown / Speculation:'.\n"
                "- Prioritize synthesis over extraction: combine related evidence across sources when possible.\n"
                "- Do not simply restate snippets; infer a concise analyst memo grounded in citations.\n"
                "- Keep each section to 1-3 high-signal claims."
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
    return value.strip()


def _parse_llm_structured_payload(content: str) -> dict[str, list[dict[str, Any]]] | None:
    try:
        parsed = json.loads(content)
    except json.JSONDecodeError:
        return None

    if not isinstance(parsed, dict):
        return None

    alias_map = {
        "executive_summary": "executive_summary",
        "summary": "executive_summary",
        "facts": "facts",
        "fact": "facts",
        "opinions": "opinions",
        "opinion": "opinions",
        "forecasts": "forecasts",
        "forecast": "forecasts",
        "bull_case": "bull_case",
        "bullcase": "bull_case",
        "bear_case": "bear_case",
        "bearcase": "bear_case",
        "uncertainties": "uncertainties",
        "uncertainty": "uncertainties",
    }
    normalized: dict[str, list[dict[str, Any]]] = {key: [] for key, _ in SECTION_ORDER}

    for raw_key, raw_value in parsed.items():
        if not isinstance(raw_key, str):
            continue
        key = alias_map.get(raw_key.strip().lower())
        if key is None or not isinstance(raw_value, list):
            continue

        entries: list[dict[str, Any]] = []
        for item in raw_value:
            if isinstance(item, str):
                claim = item.strip()
                if claim:
                    entries.append({"claim": claim, "citations": []})
                continue
            if not isinstance(item, dict):
                continue

            claim_raw = item.get("claim")
            if not isinstance(claim_raw, str):
                continue
            claim = claim_raw.strip()
            if not claim:
                continue

            citations_raw = item.get("citations", [])
            citations: list[str] = []
            if isinstance(citations_raw, list):
                for citation in citations_raw:
                    if isinstance(citation, str):
                        normalized_url = _normalize_url(citation)
                        if normalized_url:
                            citations.append(normalized_url)
            elif isinstance(citations_raw, str):
                normalized_url = _normalize_url(citations_raw)
                if normalized_url:
                    citations.append(normalized_url)

            entries.append({"claim": claim, "citations": citations})

        normalized[key] = entries

    return normalized


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


def _render_validated_sections(
    structured: dict[str, list[dict[str, Any]]],
    sources: list[CitedSource],
) -> str:
    source_by_url = {_normalize_url(source.tweet_url): source for source in sources}
    lines: list[str] = []

    for section_key, section_title in SECTION_ORDER:
        section_entries = structured.get(section_key, [])
        section_lines: list[str] = []

        for entry in section_entries[:6]:
            claim_raw = entry.get("claim")
            citations_raw = entry.get("citations", [])
            if not isinstance(claim_raw, str):
                continue
            claim = claim_raw.strip()
            if not claim:
                continue

            citations: list[str] = []
            if isinstance(citations_raw, list):
                for citation in citations_raw:
                    if not isinstance(citation, str):
                        continue
                    normalized_url = _normalize_url(citation)
                    if normalized_url in source_by_url:
                        citations.append(normalized_url)

            if not citations:
                section_lines.append(f"Unknown / Speculation: {claim}")
                continue

            grounded = any(
                _has_claim_source_overlap(claim=claim, snippet=source_by_url[citation].snippet) for citation in citations
            )
            if not grounded:
                section_lines.append(f"Unknown / Speculation: {claim}")
                continue

            citation_blob = ", ".join(citations[:2])
            section_lines.append(f"{claim} (source: {citation_blob})")

        if not section_lines:
            section_lines = ["Unknown / Speculation: no directly supported claims."]

        lines.append(f"{section_title}: {' '.join(section_lines)}")

    return "\n\n".join(lines)


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
            {"role": "system", "content": GROUNDED_ANALYSIS_PROMPT},
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
    if not deduped_sources:
        return _unknown_bundle("No cited tweets matched this request.")

    settings = get_settings()
    resolved_model = chat_model or settings.chat_model
    if _uses_local_chat_model(resolved_model):
        return AnswerBundle(answer_text=_build_rule_based_answer(question, deduped_sources), cited_sources=deduped_sources)

    raw_answer = _build_openai_answer(
        question,
        deduped_sources,
        chat_model=resolved_model,
        reasoning_effort=reasoning_effort,
        api_key=api_key,
        history=history or [],
    )
    structured = _parse_llm_structured_payload(raw_answer)
    if structured is None:
        return AnswerBundle(
            answer_text=_build_rule_based_answer(question, deduped_sources),
            cited_sources=deduped_sources,
        )

    return AnswerBundle(
        answer_text=_render_validated_sections(structured, deduped_sources),
        cited_sources=deduped_sources,
    )
