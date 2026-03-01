from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_expiry_time,
    verify_password,
)
from app.dependencies import get_current_user
from app.modules.users.models import User

from .schemas import SRefreshTokenRequest, STokenResponse, SUserLogin, SUserRegister, SUserResponse
from .services import RefreshTokenService, UserService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=SUserResponse)
async def register(data: SUserRegister, db: AsyncSession = Depends(get_db)):
    user_dict = data.model_dump()
    us = UserService(db)
    user = await us.create(**user_dict)
    return user


@router.post("/login", response_model=STokenResponse)
async def login(data: SUserLogin, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalars().first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id, user.token_version)
    rts = RefreshTokenService(db)
    refresh_token = create_refresh_token()
    refresh_token_exp = get_refresh_expiry_time()
    await rts.save(refresh_token, user.id, refresh_token_exp)

    return STokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=STokenResponse)
async def refresh(request: SRefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token = request.refresh_token

    rts = RefreshTokenService(db)
    revoked = await rts.check_and_revoke(token)

    access_token = create_access_token(revoked.user_id, revoked.user.token_version)
    refresh_token = create_refresh_token()
    refresh_token_exp = get_refresh_expiry_time()
    await rts.save(refresh_token, revoked.user_id, refresh_token_exp)
    return STokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: SRefreshTokenRequest, db: AsyncSession = Depends(get_db)):
    token = request.refresh_token
    rts = RefreshTokenService(db)
    await rts.revoke(token)


@router.post("/logout_all", status_code=status.HTTP_204_NO_CONTENT)
async def logout_all(
    db: AsyncSession = Depends(get_db), current_user: User = Depends(get_current_user)
):
    us = UserService(db)
    await us.update_token_version(current_user.id)
    rts = RefreshTokenService(db)
    await rts.revoke_all(current_user.id)
