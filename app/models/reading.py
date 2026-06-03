from __future__ import annotations

from datetime import date, datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Date, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SyncMixin, TimestampMixin


class Reading(TimestampMixin, SyncMixin, Base):
    __tablename__ = "readings"

    lectura_anterior: Mapped[float | None] = mapped_column(Float, nullable=True)
    lectura_actual: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Null cuando hay motivo_no_lectura_id (no se pudo tomar lectura)"""
    consumo: Mapped[float | None] = mapped_column(Float, nullable=True)
    """Consumo calculado (lectura_actual - lectura_anterior)"""
    consumo_calculado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    """Consumo usado para validación (puede diferir de consumo si hay ajustes)"""
    consumo_categoria: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """Categoría de consumo: Girado Sentido Contrario, Consumo Bajo, Consumo Normal, Consumo Alto, Consumo Elevado"""
    promedio_historico_usado: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    """Promedio histórico de consumo del medidor usado para calcular porcentaje"""
    timestamp_validacion: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    """Timestamp de cuando se validó la lectura"""
    usuario_id: Mapped[Optional[UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    """ID del usuario que realizó la validación (normalmente el lector que tomó la lectura)"""
    version_app: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    """Versión de la aplicación que procesó la lectura"""
    fecha_lectura: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    foto_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones_admin: Mapped[str | None] = mapped_column(Text, nullable=True)
    """Notas internas del admin/supervisor"""
    gps_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    metodo_captura: Mapped[str] = mapped_column(
        String(50), default="manual", nullable=False
    )
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    """Identificador del dispositivo móvil que originó la lectura"""

    estado_validacion: Mapped[str] = mapped_column(
        String(50), default="pendiente", nullable=False, index=True
    )
    """Valores: pendiente | validada | requiere_revision | rechazada"""

    estado_sync: Mapped[str] = mapped_column(
        String(50), default="pending", nullable=False, index=True
    )
    """Valores: pending | synced | conflict | error"""

    synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    meter_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lector_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    motivo_no_lectura_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("no_read_reasons.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    """FK al catálogo de motivos cuando no se pudo tomar la lectura"""

    meter = relationship("Meter", back_populates="readings")
    lector = relationship("User", foreign_keys=[lector_id], back_populates="readings")
    motivo_no_lectura = relationship("NoReadReason", lazy="joined")
    usuario = relationship("User", foreign_keys=[usuario_id])
