import pytest

from app.core.config import Settings
from app.core.cors import resolve_cors_origin_regex, resolve_cors_origins, validate_cors_settings


def test_exact_extension_ids_are_added_to_cors_origins() -> None:
    settings = Settings(
        CORS_ALLOW_ORIGINS="https://app.example.com",
        CORS_EXTENSION_IDS="abcdefghijklmnopabcdefghijklmnop",
        CORS_ALLOW_ORIGIN_REGEX="",
    )

    assert resolve_cors_origins(settings) == [
        "https://app.example.com",
        "chrome-extension://abcdefghijklmnopabcdefghijklmnop",
    ]
    assert resolve_cors_origin_regex(settings) is None
    validate_cors_settings(settings)


def test_invalid_extension_id_is_rejected() -> None:
    settings = Settings(CORS_EXTENSION_IDS="not-an-extension-id")

    with pytest.raises(RuntimeError, match="Invalid Chrome extension ID"):
        validate_cors_settings(settings)


def test_production_rejects_broad_extension_origin_regex() -> None:
    settings = Settings(
        APP_ENV="production",
        CORS_ALLOW_ORIGINS="https://app.example.com",
        CORS_ALLOW_ORIGIN_REGEX=r"^chrome-extension://[a-z]{32}$",
    )

    with pytest.raises(RuntimeError, match="Invalid production CORS config"):
        validate_cors_settings(settings)


def test_production_accepts_exact_extension_ids_without_regex() -> None:
    settings = Settings(
        APP_ENV="production",
        CORS_ALLOW_ORIGINS="https://app.example.com",
        CORS_ALLOW_ORIGIN_REGEX="",
        CORS_EXTENSION_IDS="abcdefghijklmnopabcdefghijklmnop",
    )

    validate_cors_settings(settings)
