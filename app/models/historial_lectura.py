from __future__ import annotations

from datetime import date

from sqlalchemy import Date, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class HistorialLectura(Base):
    __tablename__ = "historial_lecturas"

    id_lectura: Mapped[str] = mapped_column(String(50), primary_key=True, index=True)
    nom_aps: Mapped[str | None] = mapped_column(Text, nullable=True)
    nom_ciudad: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_tercero: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nom_lector: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_predio: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    nuis: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    nom_barrio: Mapped[str | None] = mapped_column(Text, nullable=True)
    direccion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[date | None] = mapped_column(Date, nullable=True)
    lectura_ant: Mapped[float | None] = mapped_column(Float, nullable=True)
    lectura: Mapped[float | None] = mapped_column(Float, nullable=True)
    consumo: Mapped[float | None] = mapped_column(Float, nullable=True)
    solucion_consumo: Mapped[str | None] = mapped_column(String(100), nullable=True)
    promedio: Mapped[float | None] = mapped_column(Float, nullable=True)
    id_novedad: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nom_suscriptor: Mapped[str | None] = mapped_column(Text, nullable=True)
    serial_medidor: Mapped[str | None] = mapped_column(String(100), nullable=True)
    nom_marca: Mapped[str | None] = mapped_column(Text, nullable=True)
    id_ciclo: Mapped[str | None] = mapped_column(String(50), nullable=True)
    orden_lectura: Mapped[str | None] = mapped_column(String(50), nullable=True)
    ruta_lectura: Mapped[str | None] = mapped_column(String(100), nullable=True)
    consumo_1: Mapped[float | None] = mapped_column(Float, nullable=True)
    consumo_2: Mapped[float | None] = mapped_column(Float, nullable=True)
    consumo_3: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(20), server_default="pendiente", default="pendiente", nullable=False)
    observacion: Mapped[str | None] = mapped_column(Text, nullable=True)
    fotos: Mapped[str | None] = mapped_column(Text, nullable=True)
    fotos_pendientes: Mapped[int | None] = mapped_column(Integer, default=0)
