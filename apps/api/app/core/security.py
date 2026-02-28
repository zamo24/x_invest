import hashlib
import hmac
import secrets

TOKEN_PREFIX = "xic_pat_"


def create_plaintext_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_token(token: str, pepper: str) -> str:
    digest = hmac.new(pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def fingerprint_token(token: str) -> str:
    if len(token) < 10:
        return "invalid"
    return f"{token[:10]}...{token[-4:]}"
