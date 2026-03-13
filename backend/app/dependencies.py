from typing import Any

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.db import get_db
from app.core.security import decode_token
from app.core.storage import create_s3_client
from app.modules.users.exceptions import InvalidTokenError
from app.modules.users.models import User

auth_scheme = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(auth_scheme),
    db: AsyncSession = Depends(get_db),
):
    token = credentials.credentials
    payload = decode_token(token)

    if payload is None:
        raise InvalidTokenError

    user_id = payload.get("sub")
    token_version_in_token = payload.get("tv")

    if user_id is None or token_version_in_token is None:
        raise InvalidTokenError

    stmt = select(User).where(
        User.id == user_id, User.token_version == token_version_in_token, User.is_active == True
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise InvalidTokenError

    return user


def get_s3_client() -> Any:
    return create_s3_client()
