from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

# User


class SUserRegister(BaseModel):
    username: str = Field(min_length=3, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SUserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class SUserResponse(BaseModel):
    id: UUID
    username: str
    email: EmailStr
    role: str
    created_at: datetime
    last_login_at: datetime
    is_active: bool

    class Config:
        from_attributes = True


# RefreshToken


class SRefreshTokenRequest(BaseModel):
    refresh_token: str


class STokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class SLogoutRequest(BaseModel):
    refresh_token: str
