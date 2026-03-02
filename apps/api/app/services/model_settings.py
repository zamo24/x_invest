from __future__ import annotations

import base64
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import UUID

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.models import User, UserModelSettings
from app.schemas.model_settings import (
    InferenceMode,
    ModelProvider,
    ReasoningEffort,
    ModelSettingsResponse,
    ModelSettingsUpdateRequest,
)

SUPPORTED_BYOK_PROVIDERS: tuple[ModelProvider, ...] = ("openai",)
SUPPORTED_REASONING_EFFORTS: tuple[ReasoningEffort, ...] = ("none", "minimal", "low", "medium", "high", "xhigh")


class ModelSettingsError(ValueError):
    pass


@dataclass
class ChatExecutionConfig:
    inference_mode: InferenceMode
    provider: ModelProvider
    model: str
    reasoning_effort: ReasoningEffort
    api_key: str | None


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _hosted_models(settings: Settings) -> list[str]:
    configured = _parse_csv(settings.hosted_chat_models)
    if not configured:
        return [settings.chat_model]
    if settings.chat_model not in configured:
        configured.append(settings.chat_model)
    return configured


def _default_model(settings: Settings) -> str:
    return settings.chat_model


def _hosted_provider(settings: Settings) -> ModelProvider:
    return "openai"


def _supports_reasoning_effort(model: str) -> bool:
    return model.strip().lower().startswith("gpt-5")


def _normalize_fernet_key(raw_value: str) -> bytes:
    raw = raw_value.strip().encode("utf-8")
    if len(raw) == 44:
        try:
            decoded = base64.urlsafe_b64decode(raw)
            if len(decoded) == 32:
                return raw
        except Exception:
            pass
    return base64.urlsafe_b64encode(hashlib.sha256(raw).digest())


def _fernet() -> Fernet:
    settings = get_settings()
    if not settings.byok_encryption_key:
        raise ModelSettingsError("BYOK encryption is not configured. Set BYOK_ENCRYPTION_KEY.")
    return Fernet(_normalize_fernet_key(settings.byok_encryption_key))


def encrypt_api_key(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_api_key(ciphertext: str) -> str:
    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ModelSettingsError("Stored BYOK API key could not be decrypted.") from exc


def get_or_create_user_model_settings(db: Session, user_id: UUID) -> UserModelSettings:
    record = db.get(UserModelSettings, user_id)
    if record is not None:
        return record

    settings = get_settings()
    record = UserModelSettings(
        user_id=user_id,
        inference_mode="hosted",
        preferred_provider="openai",
        preferred_model=_default_model(settings),
        reasoning_effort="medium",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def serialize_model_settings(record: UserModelSettings) -> ModelSettingsResponse:
    settings = get_settings()
    hosted_models = _hosted_models(settings)
    preferred_model = record.preferred_model or _default_model(settings)
    return ModelSettingsResponse(
        inference_mode=record.inference_mode,
        preferred_provider=record.preferred_provider,
        preferred_model=preferred_model,
        reasoning_effort=record.reasoning_effort,  # type: ignore[arg-type]
        byo_openai_key_configured=bool(record.byo_openai_api_key_encrypted),
        byo_openai_key_last4=record.byo_openai_api_key_last4,
        hosted_provider=_hosted_provider(settings),
        hosted_default_model=_default_model(settings),
        hosted_available_models=hosted_models,
        available_reasoning_efforts=list(SUPPORTED_REASONING_EFFORTS),
        supported_byok_providers=list(SUPPORTED_BYOK_PROVIDERS),
    )


def _validate_provider(provider: str) -> ModelProvider:
    normalized = provider.strip().lower()
    if normalized not in SUPPORTED_BYOK_PROVIDERS:
        supported = ", ".join(SUPPORTED_BYOK_PROVIDERS)
        raise ModelSettingsError(f"Unsupported provider '{provider}'. Supported providers: {supported}.")
    return normalized  # type: ignore[return-value]


def _validate_reasoning_effort(value: str) -> ReasoningEffort:
    normalized = value.strip().lower()
    if normalized not in SUPPORTED_REASONING_EFFORTS:
        supported = ", ".join(SUPPORTED_REASONING_EFFORTS)
        raise ModelSettingsError(f"Unsupported reasoning_effort '{value}'. Supported values: {supported}.")
    return normalized  # type: ignore[return-value]


def update_model_settings(
    *,
    db: Session,
    user: User,
    payload: ModelSettingsUpdateRequest,
) -> ModelSettingsResponse:
    settings = get_settings()
    record = get_or_create_user_model_settings(db, user.id)

    if payload.preferred_provider is not None:
        record.preferred_provider = _validate_provider(payload.preferred_provider)

    if payload.preferred_model is not None:
        cleaned_model = payload.preferred_model.strip()
        if not cleaned_model:
            raise ModelSettingsError("preferred_model cannot be empty.")
        record.preferred_model = cleaned_model

    if payload.reasoning_effort is not None:
        record.reasoning_effort = _validate_reasoning_effort(payload.reasoning_effort)

    if payload.byo_openai_api_key is not None:
        plaintext = payload.byo_openai_api_key.strip()
        if not plaintext:
            raise ModelSettingsError("byo_openai_api_key cannot be empty.")
        record.byo_openai_api_key_encrypted = encrypt_api_key(plaintext)
        record.byo_openai_api_key_last4 = plaintext[-4:] if len(plaintext) >= 4 else plaintext
        record.byo_openai_api_key_updated_at = datetime.now(timezone.utc)

    if payload.clear_byo_openai_api_key:
        record.byo_openai_api_key_encrypted = None
        record.byo_openai_api_key_last4 = None
        record.byo_openai_api_key_updated_at = None

    if payload.inference_mode is not None:
        record.inference_mode = payload.inference_mode

    hosted_models = _hosted_models(settings)
    if record.inference_mode == "hosted":
        if record.preferred_model not in hosted_models:
            record.preferred_model = _default_model(settings)
    else:
        if record.preferred_provider not in SUPPORTED_BYOK_PROVIDERS:
            raise ModelSettingsError("BYOK mode currently supports OpenAI only.")
        if not record.byo_openai_api_key_encrypted:
            raise ModelSettingsError("BYOK mode requires an OpenAI API key.")

    db.add(record)
    db.commit()
    db.refresh(record)
    return serialize_model_settings(record)


def resolve_chat_execution(
    *,
    db: Session,
    user: User,
    requested_provider: str | None,
    requested_model: str | None,
) -> ChatExecutionConfig:
    settings = get_settings()
    hosted_models = _hosted_models(settings)
    record = get_or_create_user_model_settings(db, user.id)
    inference_mode: InferenceMode = record.inference_mode  # type: ignore[assignment]

    preferred_provider = _validate_provider(record.preferred_provider)
    provider = _validate_provider(requested_provider) if requested_provider else preferred_provider
    model = (requested_model or record.preferred_model or _default_model(settings)).strip()
    if not model:
        model = _default_model(settings)
    reasoning_effort = _validate_reasoning_effort(record.reasoning_effort or "medium")
    if not _supports_reasoning_effort(model):
        reasoning_effort = "none"

    if inference_mode == "hosted":
        if model not in hosted_models:
            raise ModelSettingsError("Requested model is not available in hosted mode.")
        return ChatExecutionConfig(
            inference_mode="hosted",
            provider=_hosted_provider(settings),
            model=model,
            reasoning_effort=reasoning_effort,
            api_key=None,
        )

    if provider != "openai":
        raise ModelSettingsError("BYOK mode currently supports OpenAI only.")
    if not record.byo_openai_api_key_encrypted:
        raise ModelSettingsError("BYOK mode requires an OpenAI API key.")

    return ChatExecutionConfig(
        inference_mode="byok",
        provider="openai",
        model=model,
        reasoning_effort=reasoning_effort,
        api_key=decrypt_api_key(record.byo_openai_api_key_encrypted),
    )
