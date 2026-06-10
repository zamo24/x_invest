from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet

from app.core.config import get_settings


def _fernet() -> Fernet:
    secret = get_settings().x_token_encryption_key
    if not secret:
        raise RuntimeError("X_TOKEN_ENCRYPTION_KEY is required for X OAuth.")
    try:
        return Fernet(secret.encode("ascii"))
    except ValueError:
        derived = base64.urlsafe_b64encode(hashlib.sha256(secret.encode("utf-8")).digest())
        return Fernet(derived)


def encrypt_x_secret(value: str) -> str:
    return _fernet().encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_x_secret(value: str) -> str:
    return _fernet().decrypt(value.encode("ascii")).decode("utf-8")
