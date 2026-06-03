from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class NoReadReasonBase(BaseModel):
    codigo: int = Field(..., examples=[1])
    descripcion: str = Field(..., min_length=1, examples=["Usuario ausente en el momento de la lectura"])
    activo: bool = True
    sugiere_promedio: bool = False

    @field_validator("sugiere_promedio", mode="before")
    @classmethod
    def coerce_sugiere_promedio(cls, v: object) -> bool:
        if isinstance(v, str):
            return v.upper() == "S"
        return bool(v)


class NoReadReasonCreate(NoReadReasonBase):
    pass


class NoReadReasonUpdate(BaseModel):
    codigo: int | None = Field(None, examples=[1])
    descripcion: str | None = Field(None, min_length=1)
    activo: bool | None = None


class NoReadReasonOut(NoReadReasonBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
