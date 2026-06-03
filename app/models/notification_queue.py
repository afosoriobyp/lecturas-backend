from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class NotificationQueue(Base):
    """Payloads de notificación pendientes para Telegram (no envía aún)."""

    __tablename__ = "notification_queue"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(nullable=True)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)
    """Valores: sync_complete | anomaly_detected | reading_confirmed"""

    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    cuerpo: Mapped[str] = mapped_column(Text, nullable=False)
    payload_data: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    enviado: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    enviado_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
