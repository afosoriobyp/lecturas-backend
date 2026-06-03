from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, Field


class AppError(BaseModel):
    code: str = Field(..., description="Código de error máquina-legible")
    message: str = Field(..., description="Mensaje legible para el frontend")
    details: dict[str, Any] = Field(default_factory=dict, description="Contexto adicional del error")
    trace_id: str = Field(..., description="UUID de trazabilidad para correlacionar logs")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Marca de tiempo ISO 8601 UTC",
    )
