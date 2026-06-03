from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field


class ReadingEstadoUpdate(BaseModel):
    estado_validacion: str = Field(
        ..., pattern=r"^(validada|requiere_revision)$"
    )


class ReadingObservacionAdmin(BaseModel):
    observacion: str = Field(..., min_length=1, max_length=1000)
