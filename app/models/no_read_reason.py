from __future__ import annotations

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class NoReadReason(TimestampMixin, Base):
    __tablename__ = "no_read_reasons"

    codigo: Mapped[int] = mapped_column(
        Integer, unique=True, nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    activo: Mapped[bool] = mapped_column(default=True, nullable=False)
    foto: Mapped[str | None] = mapped_column(String(2), nullable=True)
    sugiere_promedio: Mapped[str] = mapped_column(String(2), nullable=False, default="N")
