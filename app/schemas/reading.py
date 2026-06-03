from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import GPSPoint


class ReadingBase(BaseModel):
    lectura_anterior: float = Field(..., ge=0)
    lectura_actual: float | None = Field(None, ge=0)
    """Null cuando hay motivo_no_lectura_id"""
    consumo: float | None = Field(None, ge=0)
    fecha_lectura: date
    foto_url: str | None = None
    observaciones: str | None = Field(None, max_length=500)
    gps_json: GPSPoint | None = None
    metodo_captura: str = Field(
        default="manual",
        pattern=r"^(manual|foto|telegram|api)$",
    )
    motivo_no_lectura_id: UUID | None = None


class ReadingCreate(ReadingBase):
    meter_id: UUID
    lector_id: UUID | None = None


class ReadingUpdate(BaseModel):
    lectura_anterior: float | None = Field(None, ge=0)
    lectura_actual: float | None = Field(None, ge=0)
    consumo: float | None = Field(None, ge=0)
    fecha_lectura: date | None = None
    foto_url: str | None = None
    observaciones: str | None = None
    gps_json: GPSPoint | None = None
    metodo_captura: str | None = Field(
        None, pattern=r"^(manual|foto|telegram|api)$"
    )
    motivo_no_lectura_id: UUID | None = None


class ReadingOut(ReadingBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    meter_id: UUID
    lector_id: UUID | None
    motivo_no_lectura_id: UUID | None
    observaciones_admin: str | None
    consumo: float | None
    consumo_calculado: float | None
    consumo_categoria: str | None
    promedio_historico_usado: float | None
    timestamp_validacion: datetime | None
    usuario_id: UUID | None
    version_app: str | None
    estado_sync: str
    created_at: datetime
    updated_at: datetime
