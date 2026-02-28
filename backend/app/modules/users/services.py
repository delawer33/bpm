import hashlib
import uuid
from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .exceptions import RefreshTokenExistsError
from .models import RefreshToken


class RefreshTokenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def revoke(self, token: str):
        pass

    async def save(self, token: str, user_id: uuid.UUID, expires_at: datetime) -> RefreshToken:
        hashed = hashlib.sha256(token.encode()).hexdigest()
        t = RefreshToken(user_id=user_id, token_hash=hashed, expires_at=expires_at)
        try:
            self.db.add(t)
            await self.db.commit()
            await self.db.refresh(t)
        except IntegrityError:
            await self.db.rollback()
            raise RefreshTokenExistsError
        return t

    def check_and_revoke(self, token: str):
        pass
