from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RutaBase(BaseModel):
    codigo: str = Field(..., min_length=1, max_length=50, examples=["R-001"])
    nombre: str = Field(..., min_length=1, max_length=200, examples=["Ruta Norte"])
    zona: str | None = Field(None, max_length=100)


class RutaCreate(RutaBase):
    pass


class RutaUpdate(BaseModel):
    codigo: str | None = Field(None, min_length=1, max_length=50)
    nombre: str | None = Field(None, min_length=1, max_length=200)
    zona: str | None = Field(None, max_length=100)


class RutaOut(RutaBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
