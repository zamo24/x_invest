import hashlib
import hmac
import re
import secrets

TOKEN_PREFIX = "xic_pat_"
TOKEN_RE = re.compile(rf"^{TOKEN_PREFIX}[A-Za-z0-9_-]{{20,}}$")


def create_plaintext_token() -> str:
    return f"{TOKEN_PREFIX}{secrets.token_urlsafe(32)}"


def hash_token(token: str, pepper: str) -> str:
    digest = hmac.new(pepper.encode("utf-8"), token.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def fingerprint_token(token: str) -> str:
    if len(token) < 10:
        return "invalid"
    return f"{token[:10]}...{token[-4:]}"


def is_well_formed_pat(token: str) -> bool:
    if not token:
        return False
    return TOKEN_RE.match(token) is not None
