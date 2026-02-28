# from app.modules.users.schemas import RefreshTokenRequest, TokenResponse, UserLogin
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_refresh_expiry_time,
    verify_password,
)
from app.modules.users.models import User

from .services import RefreshTokenService

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(email: str, password: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalars().first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    access_token = create_access_token(user.id, user.token_version)
    rts = RefreshTokenService(db)
    refresh_token = create_refresh_token()
    refresh_token_exp = get_refresh_expiry_time()
    await rts.save(refresh_token, user.id, refresh_token_exp)

    return JSONResponse({"access_token": access_token, "refresh_token": refresh_token})


#
#
# # Refresh endpoint
# @router.post("/refresh", response_model=TokenResponse)
# async def refresh(request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)):
#     token = request.refresh_token
#     payload = decode_token(token)
#     if payload is None or payload.get("type") != "refresh":
#         raise HTTPException(status_code=401, detail="Invalid token")
#
#     tv = payload.get("tv")
#     uid = payload.get("sub")
#     if tv is None or uid is None:
#         raise HTTPException(status_code=401, detail="Invalid token")
#
#     result = await db.execute(select(User).where(User.id == uid))
#     user = result.scalars().first()
#     if not user or user.token_version != tv:
#         raise HTTPException(status_code=401, detail="Token revoked")
#
#     access_token = create_access_token(user.id, user.token_version)
#     refresh_token = create_refresh_token(user.id, user.token_version)
#     return TokenResponse(access_token=access_token, refresh_token=refresh_token)
#
#
# @router.post("/logout")
# async def logout(user_id: int, db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(User).where(User.id == user_id))
#     user = result.scalars().first()
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
#
#     user.token_version += 1
#     db.add(user)
#     await db.commit()
#     return {"msg": "Logged out successfully"}
