from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, examples=["jperez"])
    email: EmailStr | None = Field(None, examples=["jperez@example.com"])
    full_name: str | None = Field(None, max_length=255, examples=["Juan Pérez"])
    rol: str = Field(default="lector", pattern=r"^(admin|supervisor|lector|auditor)$")
    is_active: bool = True
    id_tercero: str | None = Field(None, max_length=50)
    telegram_id: int | None = Field(None, ge=0)
    telegram_username: str | None = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128, examples=["Str0ng!Pass"])


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = None
    rol: str | None = Field(None, pattern=r"^(admin|supervisor|lector|auditor)$")
    is_active: bool | None = None
    id_tercero: str | None = Field(None, max_length=50)
    telegram_id: int | None = None
    telegram_username: str | None = None


class UserOut(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class UserOutDetailed(UserOut):
    telegram_chat_id: int | None = None
