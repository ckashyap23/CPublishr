from __future__ import annotations

import base64
import hashlib
import hmac
import os
from datetime import UTC, datetime, timedelta

from jose import JWTError, jwt

from src.core.config import settings

_PWD_SCHEME = "pbkdf2_sha256"
_PWD_ITERATIONS = 210_000


def hash_password(password: str) -> str:
    raw = (password or "").encode("utf-8")
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", raw, salt, _PWD_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    hash_b64 = base64.b64encode(dk).decode("ascii")
    return f"{_PWD_SCHEME}${_PWD_ITERATIONS}${salt_b64}${hash_b64}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        scheme, iterations_raw, salt_b64, hash_b64 = (stored_hash or "").split("$", 3)
        if scheme != _PWD_SCHEME:
            return False
        iterations = int(iterations_raw)
        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(hash_b64.encode("ascii"))
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", (password or "").encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_access_token(*, user_id: str) -> str:
    now = datetime.now(UTC)
    exp = now + timedelta(minutes=int(settings.auth_access_token_expire_minutes))
    payload = {
        "sub": user_id,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.auth_jwt_secret, algorithm=settings.auth_jwt_algorithm)


def decode_access_token(token: str) -> str:
    try:
        payload = jwt.decode(token, settings.auth_jwt_secret, algorithms=[settings.auth_jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid or expired access token") from exc
    user_id = str(payload.get("sub") or "").strip()
    if not user_id:
        raise ValueError("Invalid token subject")
    return user_id
