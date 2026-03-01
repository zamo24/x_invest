from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "X Investor Copilot API"
    app_env: str = "development"

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/copilot",
        alias="DATABASE_URL",
    )

    token_pepper: str = Field(default="dev-token-pepper-change-me", alias="TOKEN_PEPPER")
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000", "http://127.0.0.1:3000"],
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_origin_regex: str | None = Field(
        default=r"^chrome-extension://[a-z]{32}$",
        alias="CORS_ALLOW_ORIGIN_REGEX",
    )
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list[str] = Field(
        default_factory=lambda: ["GET", "POST", "DELETE", "OPTIONS"],
        alias="CORS_ALLOW_METHODS",
    )
    cors_allow_headers: list[str] = Field(
        default_factory=lambda: ["Authorization", "Content-Type"],
        alias="CORS_ALLOW_HEADERS",
    )
    clerk_issuer: str | None = Field(default=None, alias="CLERK_ISSUER")
    clerk_jwks_url: str | None = Field(default=None, alias="CLERK_JWKS_URL")
    clerk_audience: str | None = Field(default=None, alias="CLERK_AUDIENCE")

    embedding_model: str = Field(default="local-hash-v1", alias="EMBEDDING_MODEL")
    chat_model: str = Field(default="local-grounded-v1", alias="CHAT_MODEL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_timeout_seconds: float = Field(default=30.0, alias="OPENAI_TIMEOUT_SECONDS")
    embedding_dim: int = Field(default=256, alias="EMBEDDING_DIM")

    @field_validator("cors_allow_origins", "cors_allow_methods", "cors_allow_headers", mode="before")
    @classmethod
    def parse_csv_list(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
