"""Password hashing and opaque-token helpers. No JWT logic here — see app/auth.py."""

import hashlib
import secrets

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def generate_opaque_token() -> tuple[str, str]:
    """Returns (raw_token, sha256_hash). Only the hash is ever stored."""
    raw = secrets.token_urlsafe(32)
    return raw, hash_opaque_token(raw)


def hash_opaque_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
