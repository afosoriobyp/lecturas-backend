from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SyncJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime
    estado: str
    tipo: str
    payload: dict | None
    resultado: dict | None
    error: str | None
    intentos: int
    max_intentos: int
    procesado_at: datetime | None
