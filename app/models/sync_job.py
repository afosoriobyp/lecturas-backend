from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SyncJob(Base):
    """Cola local de trabajos de sincronización — reemplaza Redis/Celery."""

    __tablename__ = "sync_jobs"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    estado: Mapped[str] = mapped_column(
        String(50),
        default="pendiente",
        nullable=False,
        index=True,
    )
    """Valores: pendiente | procesando | completado | fallido"""

    tipo: Mapped[str] = mapped_column(String(100), nullable=False)
    """Ej: bulk_readings | update_meter_cache | generate_notifications"""

    payload: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    resultado: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    intentos: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_intentos: Mapped[int] = mapped_column(Integer, default=3, nullable=False)

    procesado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
