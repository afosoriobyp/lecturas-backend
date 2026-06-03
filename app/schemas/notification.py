from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    user_id: UUID | None
    telegram_chat_id: int | None
    tipo: str
    titulo: str
    cuerpo: str
    payload_data: dict | None
    enviado: bool
    enviado_at: datetime | None
    error: str | None
