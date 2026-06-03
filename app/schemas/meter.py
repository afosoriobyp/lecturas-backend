from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import GPSPoint
from app.schemas.reading import ReadingOut


class MeterBase(BaseModel):
    codigo_medidor: str = Field(
        ..., min_length=1, max_length=50, examples=["MTR-001"]
    )
    niud: str | None = Field(
        None, max_length=50, examples=["NIUD-001"]
    )
    direccion: str | None = Field(None, examples=["Av. Siempre Viva 742"])
    vereda: str | None = Field(None, max_length=100)
    ruta: str | None = Field(None, max_length=100)
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)
    gps_json: GPSPoint | None = None
    estado: str = Field(
        default="activo",
        pattern=r"^(activo|inactivo|mantenimiento|baja)$",
    )
    tipo: str | None = Field(
        None, pattern=r"^(agua|luz|gas)$", examples=["agua"]
    )
    ruta_id: UUID | None = None
    orden: int | None = Field(None, ge=0)


class MeterCreate(MeterBase):
    lector_id: UUID | None = None


class MeterUpdate(BaseModel):
    codigo_medidor: str | None = Field(None, min_length=1, max_length=50)
    niud: str | None = Field(None, max_length=50)
    direccion: str | None = None
    vereda: str | None = Field(None, max_length=100)
    ruta: str | None = Field(None, max_length=100)
    latitud: float | None = Field(None, ge=-90, le=90)
    longitud: float | None = Field(None, ge=-180, le=180)
    gps_json: GPSPoint | None = None
    estado: str | None = Field(
        None, pattern=r"^(activo|inactivo|mantenimiento|baja)$"
    )
    tipo: str | None = Field(
        None, pattern=r"^(agua|luz|gas)$"
    )
    lector_id: UUID | None = None
    ruta_id: UUID | None = None
    orden: int | None = Field(None, ge=0)


class MeterOut(MeterBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    lector_id: UUID | None
    ruta_id: UUID | None
    orden: int | None
    estado_sync: str
    created_at: datetime
    updated_at: datetime


class MeterOutDetailed(MeterOut):
    readings: list[ReadingOut] = []
