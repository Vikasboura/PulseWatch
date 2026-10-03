from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, description="Password must be at least 6 characters")
    full_name: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: EmailStr
    full_name: Optional[str] = None
    is_active: bool
    created_at: datetime
