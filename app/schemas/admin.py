from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class LectorOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    full_name: str | None
    email: str | None
    is_active: bool
    id_tercero: str | None


class LectorCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=100, examples=["lector1"])
    password: str = Field(..., min_length=8, max_length=128, examples=["Str0ng!Pass"])
    full_name: str | None = Field(None, max_length=255, examples=["Juan Pérez"])
    email: str | None = Field(None, examples=["jperez@example.com"])
    id_tercero: str | None = Field(None, max_length=50, examples=["T-001"])


class LectorUpdate(BaseModel):
    full_name: str | None = Field(None, max_length=255, examples=["Juan Pérez Actualizado"])
    email: str | None = Field(None, examples=["jperez-nuevo@example.com"])
    is_active: bool | None = None
    id_tercero: str | None = Field(None, max_length=50, examples=["T-002"])


class LectorResetPassword(BaseModel):
    new_password: str = Field(..., min_length=8, max_length=128, examples=["NuevaPass123!"])
