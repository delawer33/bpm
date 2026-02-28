import base64
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import get_settings

app_settings = get_settings()

ph = PasswordHasher()


def hash_password(password: str) -> str:
    return ph.hash(password)


print(hash_password("123123123"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return ph.verify(hashed_password, plain_password)
    except (VerifyMismatchError, InvalidHash):
        return False


def _create_token(data: Dict[str, Any], expires_delta: timedelta) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, app_settings.jwt_secret_key, algorithm=app_settings.jwt_algorithm)


def create_access_token(subject: uuid.UUID, token_version: int) -> str:
    return _create_token(
        {"sub": str(subject), "type": "access", "tv": token_version},
        timedelta(minutes=app_settings.jwt_expire_minutes),
    )


def create_refresh_token() -> str:
    random_bytes = secrets.token_bytes(64)
    token = base64.urlsafe_b64encode(random_bytes).rstrip(b"=").decode("utf-8")
    return token


def get_refresh_expiry_time():
    return datetime.now(timezone.utc) + timedelta(days=app_settings.jwt_refresh_expire_days)


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(
            token, app_settings.jwt_secret_key, algorithms=[app_settings.jwt_algorithm]
        )
        return payload
    except JWTError:
        return None


def get_token_subject(token: str) -> Optional[str]:
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("sub")


def get_token_version(token: str) -> Optional[int]:
    payload = decode_token(token)
    if payload is None:
        return None
    return payload.get("tv")
