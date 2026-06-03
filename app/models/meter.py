from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SyncMixin, TimestampMixin


class Meter(TimestampMixin, SyncMixin, Base):
    __tablename__ = "meters"

    codigo_medidor: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    niud: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True, index=True
    )
    """Número de Identificación Único del Dispositivo (código externo)"""

    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    vereda: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    ruta: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    latitud: Mapped[float | None] = mapped_column(nullable=True)
    longitud: Mapped[float | None] = mapped_column(nullable=True)
    gps_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    estado: Mapped[str] = mapped_column(
        String(50), default="activo", nullable=False
    )
    """Valores: activo | inactivo | mantenimiento | baja"""

    tipo: Mapped[str | None] = mapped_column(String(50), nullable=True)

    cache_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    """JSONB: {promedio_3, promedio_7, ultima_lectura, desviacion_std, fecha_ultima}"""

    ruta_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rutas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    orden: Mapped[int | None] = mapped_column(Integer, nullable=True)
    """Secuencia del medidor dentro de la ruta"""

    lector_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    lector = relationship("User", back_populates="meters")
    ruta_ref = relationship("Ruta", back_populates="meters", foreign_keys=[ruta_id])
    readings = relationship("Reading", back_populates="meter", cascade="all, delete-orphan")
