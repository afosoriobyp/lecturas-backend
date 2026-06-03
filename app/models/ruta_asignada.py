from __future__ import annotations

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class RutaAsignada(TimestampMixin, Base):
    __tablename__ = "rutas_asignadas"

    lector_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ruta_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("rutas.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    __table_args__ = (
        UniqueConstraint("lector_id", "ruta_id", name="uq_lector_ruta"),
    )

    lector = relationship("User", back_populates="asignaciones")
    ruta = relationship("Ruta", back_populates="asignaciones")
