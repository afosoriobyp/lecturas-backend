from __future__ import annotations

from sqlalchemy import BigInteger, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    username: Mapped[str] = mapped_column(
        String(100), unique=True, nullable=False, index=True
    )
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    rol: Mapped[str] = mapped_column(
        String(50), default="lector", nullable=False
    )
    """Valores: admin | supervisor | lector | auditor"""
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # id_tercero — vincula al tercero en historial_lecturas
    id_tercero: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)

    # Telegram binding
    telegram_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, nullable=True, index=True
    )
    telegram_username: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )
    telegram_chat_id: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True
    )

    meters = relationship("Meter", back_populates="lector")
    readings = relationship("Reading", foreign_keys="Reading.lector_id", back_populates="lector")
    asignaciones = relationship("RutaAsignada", back_populates="lector", cascade="all, delete-orphan")
