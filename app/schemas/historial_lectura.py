from __future__ import annotations

import json
from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator


class HistorialLecturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_lectura: str
    nuis: str | None
    nom_suscriptor: str | None
    direccion: str | None
    lectura_ant: float | None
    consumo_1: float | None
    consumo_2: float | None
    consumo_3: float | None
    fecha: date | None
    nom_lector: str | None
    ruta_lectura: str | None
    orden_lectura: str | None
    lectura: float | None
    consumo: float | None
    promedio: float | None
    solucion_consumo: str | None = None
    id_novedad: str | None = None
    status: str | None = None
    serial_medidor: str | None = None
    id_ciclo: str | None = None
    nom_barrio: str | None = None
    id_predio: str | None = None
    observacion: str | None = None
    fotos: list[str] | None = None
    fotos_pendientes: int | None = None

    @field_validator("fotos", mode="before")
    @classmethod
    def parse_fotos(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [v]
            except (json.JSONDecodeError, TypeError):
                return [v] if v else None
        return None


class HistorialLecturaListOut(BaseModel):
    total: int
    items: list[HistorialLecturaOut]


class HistorialLecturaUpdate(BaseModel):
    lectura: float | None = None
    consumo: float | None = None
    id_novedad: str | None = None
    solucion_consumo: str | None = None
    status: str | None = None
    observacion: str | None = None
    fecha: date | None = None
    fotos: list[str] | None = None
    fotos_pendientes: int | None = None

    @field_validator("id_novedad", mode="before")
    @classmethod
    def coerce_id_novedad(cls, v: Any) -> str | None:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            return str(int(v))
        return str(v) if v else None

    @field_validator("fotos", mode="before")
    @classmethod
    def parse_fotos(cls, v: Any) -> list[str] | None:
        if v is None:
            return None
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else [v]
            except (json.JSONDecodeError, TypeError):
                return [v] if v else None
        return None
