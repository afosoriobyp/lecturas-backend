from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class AsignacionCreate(BaseModel):
    lector_id: UUID
    ruta_id: UUID


class AsignacionUpdate(BaseModel):
    lector_id: UUID
    ruta_ids: list[UUID] = Field(..., min_length=1)


class AsignacionOut(BaseModel):
    id: UUID
    lector_id: UUID
    ruta_id: UUID
    ruta_codigo: str
    ruta_nombre: str
    ruta_zona: str | None
