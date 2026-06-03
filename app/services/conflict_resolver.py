from __future__ import annotations

import statistics
from datetime import date
from uuid import UUID

from sqlalchemy import Date, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ValidationException
from app.models.meter import Meter
from app.models.reading import Reading
from app.schemas.sync import BulkSyncItem, SyncResultItem


async def resolve_bulk_readings(
    db: AsyncSession,
    items: list[BulkSyncItem],
    lector_id: UUID | None = None,
    device_id: str | None = None,
    ip_address: str | None = None,
) -> tuple[list[Reading], list[SyncResultItem]]:
    """Procesa un lote de lecturas: valida, detecta duplicados, resuelve conflictos.

    Estrategia: last-write-wins por timestamp_local más reciente.
    Anomalía: si |lectura_nueva - promedio_últimas_3| > 30% → requiere_revisión.
    """
    resultados: list[SyncResultItem] = []
    lecturas_persistidas: list[Reading] = []

    for item in items:
        try:
            # 1. Buscar medidor por niud
            meter_result = await db.execute(
                select(Meter).where(Meter.niud == item.niud)
            )
            meter = meter_result.scalar_one_or_none()
            if not meter:
                resultados.append(
                    SyncResultItem(
                        niud=item.niud,
                        status="rejected",
                        message=f"Medidor con NIUD '{item.niud}' no encontrado",
                    )
                )
                continue

            # 2. Detectar duplicado por (meter_id, fecha)
            fecha_local = item.timestamp_local.date()
            dup_result = await db.execute(
                select(Reading).where(
                    Reading.meter_id == meter.id,
                    func.date_trunc("day", Reading.fecha_lectura)
                    == func.cast(fecha_local, Date),
                )
            )
            existing = dup_result.scalar_one_or_none()

            if existing:
                # Conflict: last-write-wins por timestamp_local
                if item.timestamp_local.timestamp() > existing.created_at.timestamp():
                    existing.lectura_actual = item.lectura_actual
                    existing.lectura_anterior = existing.lectura_actual
                    existing.consumo = _calcular_consumo(
                        existing.lectura_anterior, item.lectura_actual
                    )
                    existing.gps_json = item.gps.model_dump() if item.gps else None
                    existing.estado_sync = "synced"
                    existing.estado_validacion = "pendiente"
                    lecturas_persistidas.append(existing)
                    resultados.append(
                        SyncResultItem(
                            niud=item.niud,
                            status="updated",
                            reading_id=existing.id,
                            message="Actualizado por LWW",
                        )
                    )
                else:
                    resultados.append(
                        SyncResultItem(
                            niud=item.niud,
                            status="conflict",
                            message="Descartado por LWW (timestamp local anterior)",
                        )
                    )
                continue

            # 3. Calcular consumo y validar anomalía
            lectura_anterior = meter.cache_stats.get("ultima_lectura") if meter.cache_stats else None
            consumo = _calcular_consumo(lectura_anterior, item.lectura_actual)
            estado_validacion = await _detectar_anomalia(db, meter.id, item.lectura_actual)

            # 4. Crear lectura
            reading = Reading(
                meter_id=meter.id,
                lector_id=lector_id,
                lectura_anterior=lectura_anterior,
                lectura_actual=item.lectura_actual,
                consumo=consumo,
                fecha_lectura=fecha_local,
                gps_json=item.gps.model_dump() if item.gps else None,
                metodo_captura="api",
                device_id=device_id or item.device_id,
                estado_sync="synced",
                estado_validacion=estado_validacion,
            )
            db.add(reading)
            lecturas_persistidas.append(reading)

            resultados.append(
                SyncResultItem(
                    niud=item.niud,
                    status="created",
                    reading_id=reading.id,
                    message=f"Validación: {estado_validacion}",
                )
            )

        except ValidationException as e:
            resultados.append(
                SyncResultItem(
                    niud=item.niud, status="rejected", message=str(e)
                )
            )
        except Exception as e:
            resultados.append(
                SyncResultItem(
                    niud=item.niud, status="rejected", message=f"Error interno: {str(e)}"
                )
            )

    await db.flush()
    return lecturas_persistidas, resultados


async def _detectar_anomalia(
    db: AsyncSession, meter_id: UUID, lectura_actual: float
) -> str:
    """Regla: |lectura_nueva - promedio_últimas_3| > 30% → requiere_revisión."""
    result = await db.execute(
        select(Reading.lectura_actual)
        .where(
            Reading.meter_id == meter_id,
            Reading.estado_validacion.in_(["validada", "pendiente"]),
        )
        .order_by(Reading.fecha_lectura.desc())
        .limit(3)
    )
    ultimas = [row[0] for row in result.all()]

    if not ultimas:
        return "validada"

    promedio = statistics.mean(ultimas)
    if promedio == 0:
        return "validada"

    desviacion = abs(lectura_actual - promedio) / promedio
    if desviacion > 0.30:
        return "requiere_revision"

    return "validada"


def _calcular_consumo(anterior: float | None, actual: float) -> float | None:
    if anterior is not None and actual >= anterior:
        return actual - anterior
    return None
