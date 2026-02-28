from functools import lru_cache

from pydantic import Field
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

    embedding_model: str = Field(default="local-hash-v1", alias="EMBEDDING_MODEL")
    chat_model: str = Field(default="local-grounded-v1", alias="CHAT_MODEL")
    llm_api_key: str | None = Field(default=None, alias="LLM_API_KEY")
    embedding_dim: int = Field(default=256, alias="EMBEDDING_DIM")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
