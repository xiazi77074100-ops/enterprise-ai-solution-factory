"""Password hashing (argon2id), session ids and CSRF tokens."""

import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()  # argon2id with library defaults
# Verified when the login id is unknown so both paths cost the same (user enumeration via timing).
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))

PASSWORD_MIN, PASSWORD_MAX = 12, 128


def hash_password(password: str) -> str:
    if not PASSWORD_MIN <= len(password) <= PASSWORD_MAX:
        raise ValueError(f"password length must be {PASSWORD_MIN}-{PASSWORD_MAX}")
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def new_session_id() -> str:
    return secrets.token_urlsafe(32)


def hash_session_id(session_id: str) -> str:
    return hashlib.sha256(session_id.encode()).hexdigest()


def csrf_token(secret_key: str, session_id: str) -> str:
    return hmac.new(secret_key.encode(), f"csrf:{session_id}".encode(), hashlib.sha256).hexdigest()


def csrf_valid(secret_key: str, session_id: str, presented: str | None) -> bool:
    return presented is not None and hmac.compare_digest(csrf_token(secret_key, session_id), presented)
