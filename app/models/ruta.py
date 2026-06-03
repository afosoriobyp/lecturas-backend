from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Ruta(TimestampMixin, Base):
    __tablename__ = "rutas"

    codigo: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    zona: Mapped[str | None] = mapped_column(String(100), nullable=True)

    asignaciones = relationship("RutaAsignada", back_populates="ruta", cascade="all, delete-orphan")
    meters = relationship("Meter", back_populates="ruta_ref", foreign_keys="Meter.ruta_id")
