from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import GPSPoint


class BulkSyncItem(BaseModel):
    niud: str = Field(..., max_length=50)
    lectura_actual: float = Field(..., ge=0)
    timestamp_local: datetime
    gps: GPSPoint | None = None
    lector_id: UUID | None = None
    device_id: str | None = Field(None, max_length=100)
    foto_url: str | None = None
    observaciones: str | None = Field(None, max_length=500)


class BulkSyncRequest(BaseModel):
    items: list[BulkSyncItem] = Field(..., max_length=500)


class SyncResultItem(BaseModel):
    niud: str
    status: str
    """Valores: created | updated | conflict | rejected | duplicate"""
    reading_id: UUID | None = None
    message: str | None = None


class BulkSyncResponse(BaseModel):
    synced: int
    conflicts: int
    resultados: list[SyncResultItem]
    trace_id: str
    job_id: UUID | None = None

    procesados: int | None = None
    creados: int | None = None
    actualizados: int | None = None
    conflictos: int | None = None
    rechazados: int | None = None
