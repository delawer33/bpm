import hashlib
import uuid
from datetime import datetime, timezone

from sqlalchemy import text, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, hash_token

from .exceptions import (
    RefreshTokenExistsError,
    RefreshTokenNotExistError,
    RefreshTokenRevokedError,
    UserWithEmailExistsError,
)
from .models import RefreshToken, User


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, username: str, email: str, password: str) -> User:
        """
        Create user. User object in return does not contain db-generated fields.
        If you need them, run db.refresh(user)
        """
        hashed_password = hash_password(password)
        user = User(email=email, username=username, hashed_password=hashed_password)
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise UserWithEmailExistsError
        return user

    async def update_token_version(self, user_id: uuid.UUID) -> int:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(token_version=User.token_version + 1)
            .returning(User.token_version)
        )
        result = await self.db.execute(stmt)
        await self.db.commit()

        new_version = result.scalar_one()
        return new_version


class RefreshTokenService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def revoke(self, token: str):
        token_hash = hash_token(token)
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash, RefreshToken.revoked == False)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def revoke_all(self, user_id: uuid.UUID):
        stmt = (
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked == False)
            .values(revoked=True, revoked_at=datetime.now(timezone.utc))
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def save(self, token: str, user_id: uuid.UUID, expires_at: datetime) -> RefreshToken:
        hashed = hashlib.sha256(token.encode()).hexdigest()
        t = RefreshToken(user_id=user_id, token_hash=hashed, expires_at=expires_at)
        try:
            self.db.add(t)
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            raise RefreshTokenExistsError
        return t

    async def check_and_revoke(self, token: str) -> RefreshToken:
        hashed = hashlib.sha256(token.encode()).hexdigest()

        stmt = text("""
            WITH fetched AS (
                SELECT
                    rt.id              AS rt_id,
                    rt.user_id         AS rt_user_id,
                    rt.token_hash      AS rt_token_hash,
                    rt.expires_at      AS rt_expires_at,
                    rt.created_at      AS rt_created_at,
                    rt.revoked         AS rt_revoked,
                    u.id               AS u_id,
                    u.username         AS u_username,
                    u.email            AS u_email,
                    u.hashed_password  AS u_hashed_password,
                    u.role             AS u_role,
                    u.created_at       AS u_created_at,
                    u.updated_at       AS u_updated_at,
                    u.last_login_at    AS u_last_login_at,
                    u.is_active        AS u_is_active,
                    u.token_version    AS u_token_version
                FROM refresh_tokens rt
                JOIN users u ON rt.user_id = u.id
                WHERE rt.token_hash = :hash
            ),
            updated AS (
                UPDATE refresh_tokens
                SET
                    revoked = true,
                    revoked_at = now()
                WHERE id = (
                    SELECT rt_id FROM fetched
                    WHERE NOT rt_revoked AND rt_expires_at > now()
                )
                RETURNING id
            )
            SELECT fetched.*, (updated.id IS NOT NULL) AS was_revoked_now
            FROM fetched
            LEFT JOIN updated ON fetched.rt_id = updated.id
        """)

        result = await self.db.execute(stmt, {"hash": hashed})
        row = result.fetchone()

        if not row:
            raise RefreshTokenNotExistError()
        if not row.was_revoked_now:
            raise RefreshTokenRevokedError()

        await self.db.commit()

        user = User(
            id=row.u_id,
            username=row.u_username,
            email=row.u_email,
            hashed_password=row.u_hashed_password,
            role=row.u_role,
            created_at=row.u_created_at,
            updated_at=row.u_updated_at,
            last_login_at=row.u_last_login_at,
            is_active=row.u_is_active,
            token_version=row.u_token_version,
        )
        refresh_token = RefreshToken(
            id=row.rt_id,
            user_id=row.rt_user_id,
            token_hash=row.rt_token_hash,
            expires_at=row.rt_expires_at,
            created_at=row.rt_created_at,
            revoked=True,
        )
        refresh_token.user = user
        return refresh_token
