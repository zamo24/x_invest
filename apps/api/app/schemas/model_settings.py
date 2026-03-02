from typing import Literal

from pydantic import BaseModel, Field

InferenceMode = Literal["hosted", "byok"]
ModelProvider = Literal["openai"]
ReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]


class ModelSettingsResponse(BaseModel):
    inference_mode: InferenceMode
    preferred_provider: ModelProvider
    preferred_model: str
    reasoning_effort: ReasoningEffort
    byo_openai_key_configured: bool
    byo_openai_key_last4: str | None = None
    hosted_provider: ModelProvider
    hosted_default_model: str
    hosted_available_models: list[str] = Field(default_factory=list)
    available_reasoning_efforts: list[ReasoningEffort] = Field(
        default_factory=lambda: ["none", "minimal", "low", "medium", "high", "xhigh"]
    )
    supported_byok_providers: list[ModelProvider] = Field(default_factory=lambda: ["openai"])


class ModelSettingsUpdateRequest(BaseModel):
    inference_mode: InferenceMode | None = None
    preferred_provider: ModelProvider | None = None
    preferred_model: str | None = None
    reasoning_effort: ReasoningEffort | None = None
    byo_openai_api_key: str | None = None
    clear_byo_openai_api_key: bool = False
