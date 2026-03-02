from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.models import UserModelSettings
from app.db.session import SessionLocal


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_model_settings_update_and_encryption(client: TestClient, auth_context: Any) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}

    initial = client.get("/v1/model-settings", headers=headers)
    assert initial.status_code == 200, initial.text
    assert initial.json()["inference_mode"] == "hosted"

    update = client.put(
        "/v1/model-settings",
        headers=headers,
        json={
            "inference_mode": "byok",
            "preferred_provider": "openai",
            "preferred_model": "gpt-4o-mini",
            "reasoning_effort": "high",
            "byo_openai_api_key": "sk-test-1234567890",
        },
    )
    assert update.status_code == 200, update.text
    payload = update.json()
    assert payload["inference_mode"] == "byok"
    assert payload["reasoning_effort"] == "high"
    assert payload["byo_openai_key_configured"] is True
    assert payload["byo_openai_key_last4"] == "7890"

    with SessionLocal() as db:
        record = db.execute(
            select(UserModelSettings).where(UserModelSettings.user_id == UUID(auth_context.user_id))
        ).scalar_one_or_none()
        assert record is not None
        assert record.byo_openai_api_key_encrypted is not None
        assert "sk-test-1234567890" not in record.byo_openai_api_key_encrypted


def test_chat_uses_byok_api_key_when_enabled(
    client: TestClient,
    auth_context: Any,
    monkeypatch: Any,
) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}

    # Save one tweet so chat has retrievable sources and invokes model generation.
    tweet_id = f"pytest_byok_{uuid4().hex[:12]}"
    ingest_payload = {
        "capture_type": "tweet",
        "page_url": f"https://x.com/test/status/{tweet_id}",
        "root_tweet_id": tweet_id,
        "root_tweet_url": f"https://x.com/test/status/{tweet_id}",
        "tweets": [
            {
                "tweet_id": tweet_id,
                "url": f"https://x.com/test/status/{tweet_id}",
                "author_handle": "byoktester",
                "author_name": "BYOK Tester",
                "created_at": _iso_now(),
                "text": "HBM pricing momentum looks strong into next quarter.",
                "captured_at": _iso_now(),
            }
        ],
        "captured_count": 1,
        "is_partial": False,
    }
    ingest = client.post("/v1/ingest/x", headers=headers, json=ingest_payload)
    assert ingest.status_code == 200, ingest.text

    settings_update = client.put(
        "/v1/model-settings",
        headers=headers,
        json={
            "inference_mode": "byok",
            "preferred_provider": "openai",
            "preferred_model": "gpt-5-mini",
            "reasoning_effort": "high",
            "byo_openai_api_key": "sk-byok-uses-key-1234",
        },
    )
    assert settings_update.status_code == 200, settings_update.text

    observed: dict[str, Any] = {"api_key": None, "payload": None}

    def fake_call_openai_json(path: str, payload: dict[str, Any], *, api_key: str | None = None) -> dict[str, Any]:
        observed["api_key"] = api_key
        observed["payload"] = payload
        return {
            "choices": [
                {
                    "message": {
                        "content": "Facts:\n- HBM pricing momentum cited.\nOpinions:\n- Unknown / Speculation.\nForecasts:\n- Unknown / Speculation.\nBull Case:\n- Unknown / Speculation.\nBear Case:\n- Unknown / Speculation.\nUncertainties:\n- Unknown / Speculation."
                    }
                }
            ]
        }

    monkeypatch.setattr("app.services.rag.call_openai_json", fake_call_openai_json)

    chat_response = client.post(
        "/v1/chat",
        headers=headers,
        json={"message": "Summarize my HBM view", "scope": "all", "top_k": 4},
    )
    assert chat_response.status_code == 200, chat_response.text
    assert chat_response.json()["inference_mode_used"] == "byok"
    assert observed["api_key"] == "sk-byok-uses-key-1234"
    assert chat_response.json()["model_used"] == "gpt-5-mini"
    assert chat_response.json()["reasoning_effort_used"] == "high"
    assert "temperature" not in observed["payload"]
    assert observed["payload"]["reasoning_effort"] == "high"


def test_chat_structured_output_enforces_grounded_citations(
    client: TestClient,
    auth_context: Any,
    monkeypatch: Any,
) -> None:
    headers = {"Authorization": f"Bearer {auth_context.pat}"}

    tweet_id = f"pytest_ground_{uuid4().hex[:12]}"
    tweet_url = f"https://x.com/test/status/{tweet_id}"
    ingest_payload = {
        "capture_type": "tweet",
        "page_url": tweet_url,
        "root_tweet_id": tweet_id,
        "root_tweet_url": tweet_url,
        "tweets": [
            {
                "tweet_id": tweet_id,
                "url": tweet_url,
                "author_handle": "groundtester",
                "author_name": "Ground Tester",
                "created_at": _iso_now(),
                "text": "HBM capacity remains constrained in 2026.",
                "captured_at": _iso_now(),
            }
        ],
        "captured_count": 1,
        "is_partial": False,
    }
    ingest = client.post("/v1/ingest/x", headers=headers, json=ingest_payload)
    assert ingest.status_code == 200, ingest.text

    payload_obj = {
        "facts": [
            {"claim": "HBM capacity remains constrained in 2026.", "citations": [tweet_url]},
            {"claim": "Photonics demand already doubled this quarter.", "citations": [tweet_url]},
            {"claim": "Micron announced a new fab in Austin.", "citations": ["https://x.com/unknown/status/1"]},
        ],
        "opinions": [],
        "forecasts": [],
        "bull_case": [],
        "bear_case": [],
        "uncertainties": [],
    }

    def fake_call_openai_json(path: str, payload: dict[str, Any], *, api_key: str | None = None) -> dict[str, Any]:
        return {"choices": [{"message": {"content": json.dumps(payload_obj)}}]}

    monkeypatch.setattr("app.services.rag.call_openai_json", fake_call_openai_json)

    chat_response = client.post(
        "/v1/chat",
        headers=headers,
        json={"message": "Summarize", "scope": "all", "top_k": 4},
    )
    assert chat_response.status_code == 200, chat_response.text
    answer_text = chat_response.json()["answer_text"]
    assert "HBM capacity remains constrained in 2026. (source: " in answer_text
    assert "Unknown / Speculation: Photonics demand already doubled this quarter." in answer_text
    assert "Unknown / Speculation: Micron announced a new fab in Austin." in answer_text
