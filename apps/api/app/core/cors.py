import re

from app.core.config import Settings

EXTENSION_ID_RE = re.compile(r"^[a-z]{32}$")


def parse_csv(value: str | None) -> list[str]:
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def extension_origins(extension_ids: str | None) -> list[str]:
    origins: list[str] = []
    for extension_id in parse_csv(extension_ids):
        if not EXTENSION_ID_RE.fullmatch(extension_id):
            raise RuntimeError(f"Invalid Chrome extension ID in CORS_EXTENSION_IDS: {extension_id}")
        origins.append(f"chrome-extension://{extension_id}")
    return origins


def resolve_cors_origins(settings: Settings) -> list[str]:
    return list(dict.fromkeys([*parse_csv(settings.cors_allow_origins), *extension_origins(settings.cors_extension_ids)]))


def resolve_cors_origin_regex(settings: Settings) -> str | None:
    regex = (settings.cors_allow_origin_regex or "").strip()
    return regex or None


def validate_cors_settings(settings: Settings) -> None:
    allow_origins = resolve_cors_origins(settings)
    origin_regex = resolve_cors_origin_regex(settings)
    if settings.cors_allow_credentials and "*" in allow_origins:
        raise RuntimeError("Invalid CORS config: wildcard origin is not allowed when credentials are enabled.")
    if not allow_origins and not origin_regex:
        raise RuntimeError("Invalid CORS config: set at least one CORS origin, extension ID, or origin regex.")
    if settings.app_env.strip().lower() == "production" and origin_regex:
        raise RuntimeError(
            "Invalid production CORS config: disable CORS_ALLOW_ORIGIN_REGEX and configure exact CORS_EXTENSION_IDS."
        )
