from __future__ import annotations

from typing import Any

import httpx

from app.core.config import get_settings


class OpenAIServiceError(RuntimeError):
    pass


def _resolve_api_key() -> str:
    settings = get_settings()
    api_key = settings.openai_api_key or settings.llm_api_key
    if not api_key:
        raise OpenAIServiceError("Missing OpenAI API key. Set OPENAI_API_KEY or LLM_API_KEY.")
    return api_key


def call_openai_json(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    base_url = settings.openai_base_url.rstrip("/")
    url = f"{base_url}/{path.lstrip('/')}"

    headers = {
        "Authorization": f"Bearer {_resolve_api_key()}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=settings.openai_timeout_seconds)
    except httpx.HTTPError as exc:
        raise OpenAIServiceError(f"OpenAI request failed: {exc}") from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code >= 400:
        detail = data.get("error", {}).get("message") if isinstance(data, dict) else None
        raise OpenAIServiceError(
            f"OpenAI request failed with status {response.status_code}: {detail or response.text[:300]}"
        )

    if not isinstance(data, dict):
        raise OpenAIServiceError("OpenAI returned a non-JSON object.")

    return data
