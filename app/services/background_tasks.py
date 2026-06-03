from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models.meter import Meter
from app.models.notification_queue import NotificationQueue
from app.models.reading import Reading
from app.models.sync_job import SyncJob

logger = logging.getLogger(__name__)


async def process_sync_jobs() -> int:
    """Procesa trabajos pendientes en sync_jobs.
    
    Itera sobre jobs con estado='pendiente', los marca como 'procesando',
    ejecuta el handler según el tipo, y actualiza el resultado.

    Diseñado para ejecutarse como BackgroundTask después de cada bulk.
    """
    processed = 0
    async with async_session_factory() as db:
        try:
            result = await db.execute(
                select(SyncJob)
                .where(SyncJob.estado == "pendiente")
                .order_by(SyncJob.created_at.asc())
                .limit(10)
            )
            jobs = list(result.scalars().all())

            for job in jobs:
                job.estado = "procesando"
                job.intentos += 1
                await db.flush()

                try:
                    if job.tipo == "bulk_readings":
                        await _finalize_readings(db, job.payload or {})
                    elif job.tipo == "update_meter_cache":
                        await _update_meter_cache(db, job.payload or {})
                    elif job.tipo == "generate_notifications":
                        await _generate_notifications(db, job.payload or {})
                    else:
                        job.error = f"Tipo desconocido: {job.tipo}"
                        job.estado = "fallido"
                        continue

                    job.estado = "completado"
                    job.procesado_at = datetime.now(timezone.utc)
                    processed += 1
                except Exception as e:
                    logger.exception("SyncJob %s falló: %s", job.id, e)
                    job.error = str(e)
                    if job.intentos >= job.max_intentos:
                        job.estado = "fallido"
                    else:
                        job.estado = "pendiente"

            await db.commit()
        except Exception:
            await db.rollback()
            raise

    return processed


async def _finalize_readings(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Post-procesamiento de lecturas: recalcular consumos si es necesario."""
    meter_ids = payload.get("meter_ids", [])
    for mid in meter_ids:
        result = await db.execute(
            select(Reading)
            .where(
                Reading.meter_id == mid,
                Reading.estado_sync == "synced",
                Reading.estado_validacion == "validada",
            )
            .order_by(Reading.fecha_lectura.desc())
            .limit(1)
        )
        reading = result.scalar_one_or_none()
        if reading and reading.consumo is None and reading.lectura_anterior is not None:
            reading.consumo = max(0, reading.lectura_actual - (reading.lectura_anterior or 0))


async def _update_meter_cache(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Actualiza cache_stats en Meter con promedios históricos."""
    meter_ids = payload.get("meter_ids", [])
    for mid in meter_ids:
        result = await db.execute(
            select(Reading.lectura_actual)
            .where(
                Reading.meter_id == mid,
                Reading.estado_validacion == "validada",
            )
            .order_by(Reading.fecha_lectura.desc())
            .limit(7)
        )
        valores = [row[0] for row in result.all()]
        if not valores:
            continue

        cache = {
            "ultima_lectura": valores[0],
            "promedio_3": round(sum(valores[:3]) / len(valores[:3]), 2) if len(valores) >= 3 else None,
            "promedio_7": round(sum(valores) / len(valores), 2) if valores else None,
        }
        await db.execute(
            update(Meter)
            .where(Meter.id == mid)
            .values(cache_stats=cache)
        )


async def _generate_notifications(db: AsyncSession, payload: dict[str, Any]) -> None:
    """Genera payloads de notificación en notification_queue (NO envía aún)."""
    meter_ids = payload.get("meter_ids", [])
    for mid in meter_ids:
        result = await db.execute(
            select(Reading)
            .where(
                Reading.meter_id == mid,
                Reading.estado_validacion == "requiere_revision",
            )
            .order_by(Reading.created_at.desc())
            .limit(1)
        )
        reading = result.scalar_one_or_none()
        if not reading:
            continue

        meter_result = await db.execute(select(Meter).where(Meter.id == mid))
        meter = meter_result.scalar_one_or_none()
        if not meter:
            continue

        notif = NotificationQueue(
            tipo="anomaly_detected",
            titulo=f"Revisión requerida: {meter.codigo_medidor}",
            cuerpo=(
                f"Lectura de {reading.lectura_actual} supera el 30% "
                f"de desviación sobre el promedio histórico."
            ),
            payload_data={
                "meter_id": str(meter.id),
                "reading_id": str(reading.id),
                "codigo": meter.codigo_medidor,
                "lectura": reading.lectura_actual,
            },
        )
        db.add(notif)
