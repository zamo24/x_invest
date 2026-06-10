from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = Field(default="Investor Research Copilot API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_version: str = Field(default="0.1.0", alias="APP_VERSION")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/copilot",
        alias="DATABASE_URL",
    )

    token_pepper: str = Field(default="dev-token-pepper-change-me", alias="TOKEN_PEPPER")
    pat_default_ttl_days: int = Field(default=90, alias="PAT_DEFAULT_TTL_DAYS")
    pat_max_ttl_days: int = Field(default=365, alias="PAT_MAX_TTL_DAYS")
    rate_limit_enabled: bool = Field(default=True, alias="RATE_LIMIT_ENABLED")
    rate_limit_window_seconds: int = Field(default=60, alias="RATE_LIMIT_WINDOW_SECONDS")
    rate_limit_chat_requests: int = Field(default=30, alias="RATE_LIMIT_CHAT_REQUESTS")
    rate_limit_ingest_requests: int = Field(default=60, alias="RATE_LIMIT_INGEST_REQUESTS")
    rate_limit_token_requests: int = Field(default=30, alias="RATE_LIMIT_TOKEN_REQUESTS")
    cors_allow_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="CORS_ALLOW_ORIGINS",
    )
    cors_allow_origin_regex: str | None = Field(
        default=r"^chrome-extension://[a-z]{32}$",
        alias="CORS_ALLOW_ORIGIN_REGEX",
    )
    cors_extension_ids: str = Field(default="", alias="CORS_EXTENSION_IDS")
    cors_allow_credentials: bool = Field(default=True, alias="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: str = Field(default="GET,POST,PUT,PATCH,DELETE,OPTIONS", alias="CORS_ALLOW_METHODS")
    cors_allow_headers: str = Field(default="Authorization,Content-Type", alias="CORS_ALLOW_HEADERS")
    clerk_issuer: str | None = Field(default=None, alias="CLERK_ISSUER")
    clerk_jwks_url: str | None = Field(default=None, alias="CLERK_JWKS_URL")
    clerk_audience: str | None = Field(default=None, alias="CLERK_AUDIENCE")
    clerk_jwt_leeway_seconds: int = Field(default=30, alias="CLERK_JWT_LEEWAY_SECONDS")

    embedding_model: str = Field(default="local-hash-v1", alias="EMBEDDING_MODEL")
    chat_model: str = Field(default="local-grounded-v1", alias="CHAT_MODEL")
    hosted_chat_provider: str = Field(default="openai", alias="HOSTED_CHAT_PROVIDER")
    hosted_chat_models: str = Field(
        default="gpt-4o-mini,gpt-4.1-mini,gpt-5-mini,gpt-5.2",
        alias="HOSTED_CHAT_MODELS",
    )
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    openai_timeout_seconds: float = Field(default=30.0, alias="OPENAI_TIMEOUT_SECONDS")
    embedding_max_tokens: int = Field(default=6000, alias="EMBEDDING_MAX_TOKENS")
    embedding_max_chars: int = Field(default=24000, alias="EMBEDDING_MAX_CHARS")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")
    byok_encryption_key: str | None = Field(default=None, alias="BYOK_ENCRYPTION_KEY")
    x_client_id: str | None = Field(default=None, alias="X_CLIENT_ID")
    x_client_secret: str | None = Field(default=None, alias="X_CLIENT_SECRET")
    x_redirect_uri: str = Field(
        default="http://localhost:8000/v1/integrations/x/callback",
        alias="X_REDIRECT_URI",
    )
    x_token_encryption_key: str | None = Field(default=None, alias="X_TOKEN_ENCRYPTION_KEY")
    x_api_base_url: str = Field(default="https://api.x.com", alias="X_API_BASE_URL")
    x_content_revalidate_hours: int = Field(default=24, alias="X_CONTENT_REVALIDATE_HOURS")
    x_monthly_post_read_budget: int = Field(default=10000, alias="X_MONTHLY_POST_READ_BUDGET")
    x_bookmark_sync_post_limit: int = Field(default=1000, alias="X_BOOKMARK_SYNC_POST_LIMIT")
    x_integration_settings_url: str = Field(
        default="http://localhost:3000/app/settings/x",
        alias="X_INTEGRATION_SETTINGS_URL",
    )
    embedding_dim: int = Field(default=256, alias="EMBEDDING_DIM")
    retrieval_oversample_multiplier: int = Field(default=6, alias="RETRIEVAL_OVERSAMPLE_MULTIPLIER")
    retrieval_min_candidates: int = Field(default=30, alias="RETRIEVAL_MIN_CANDIDATES")
    retrieval_lexical_weight: float = Field(default=0.18, alias="RETRIEVAL_LEXICAL_WEIGHT")
    retrieval_recency_weight: float = Field(default=0.04, alias="RETRIEVAL_RECENCY_WEIGHT")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
