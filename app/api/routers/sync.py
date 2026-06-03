from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy import func, select

from app.api.dependencies import SessionDep
from app.core.exceptions import BusinessRuleError, SyncConflictError
from app.core.security import get_current_user
from app.models.meter import Meter
from app.models.sync_job import SyncJob
from app.models.user import User
from app.schemas.sync import BulkSyncRequest, BulkSyncResponse, SyncResultItem
from app.services.audit import log_action
from app.services.background_tasks import process_sync_jobs
from app.services.conflict_resolver import resolve_bulk_readings

router = APIRouter(prefix="/sync", tags=["Sincronización"])


@router.post(
    "/bulk",
    response_model=BulkSyncResponse,
    summary="Sincronización masiva de lecturas",
    description=(
        "Recibe hasta 500 lecturas, valida esquema, detecta duplicados por "
        "(niud, fecha), resuelve conflictos con last-write-wins, y encola "
        "procesamiento en segundo plano para actualizar cachés y notificaciones."
    ),
)
async def bulk_sync(
    db: SessionDep,
    payload: BulkSyncRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    trace_id = getattr(request.state, "trace_id", "N/A")

    lecturas, resultados = await resolve_bulk_readings(
        db,
        items=payload.items,
        lector_id=current_user.id,
        device_id=None,
        ip_address=request.client.host if request.client else None,
    )

    counts = {"created": 0, "updated": 0, "conflict": 0, "rejected": 0}
    for r in resultados:
        if r.status in counts:
            counts[r.status] += 1

    conflict_items = [r for r in resultados if r.status == "conflict"]
    anomaly_items = [
        r for r in resultados
        if r.status == "rejected" and r.message and "requiere" in r.message.lower()
    ]

    if conflict_items and counts["created"] == 0 and counts["updated"] == 0:
        raise SyncConflictError(
            message="Se detectaron conflictos de sincronización — elija acción",
            details={
                "conflicts": [
                    {
                        "niud": c.niud,
                        "message": c.message,
                    }
                    for c in conflict_items
                ],
            },
        )

    if anomaly_items and counts["created"] == 0 and counts["updated"] == 0:
        raise BusinessRuleError(
            code="SYNC_ANOMALY",
            message="Lecturas fuera de rango histórico — requieren revisión",
            details={
                "requires_review": True,
                "items": [
                    {
                        "niud": a.niud,
                        "message": a.message,
                    }
                    for a in anomaly_items
                ],
            },
        )

    meter_ids = list(set(str(l.meter_id) for l in lecturas))
    if meter_ids:
        job = SyncJob(
            tipo="bulk_readings",
            estado="pendiente",
            payload={"meter_ids": meter_ids, "count": len(lecturas)},
        )
        db.add(job)
        await db.flush()
        background_tasks.add_task(process_sync_jobs)

    await log_action(
        db,
        accion="sync.bulk",
        entidad_tipo="sync",
        actor_id=str(current_user.id),
        detalle={
            "total": len(payload.items),
            "creados": counts["created"],
            "conflictos": counts["conflict"],
            "rechazados": counts["rejected"],
        },
        ip_address=request.client.host if request.client else None,
    )

    return BulkSyncResponse(
        synced=counts["created"] + counts["updated"],
        conflicts=counts["conflict"],
        procesados=len(resultados),
        creados=counts["created"],
        actualizados=counts["updated"],
        conflictos=counts["conflict"],
        rechazados=counts["rejected"],
        resultados=resultados,
        trace_id=trace_id,
    )


@router.get(
    "/status",
    summary="Estado de sincronización",
)
async def sync_status(
    db: SessionDep,
    current_user: User = Depends(get_current_user),
):
    """Retorna métricas de sincronización: pendientes, errores, totales."""
    total = await db.scalar(select(func.count()).select_from(SyncJob))
    pendientes = await db.scalar(
        select(func.count()).where(SyncJob.estado == "pendiente")
    )
    fallidos = await db.scalar(
        select(func.count()).where(SyncJob.estado == "fallido")
    )

    return {
        "total_jobs": total or 0,
        "pendientes": pendientes or 0,
        "fallidos": fallidos or 0,
    }


@router.post(
    "/force/{entity_type}/{entity_id}",
    summary="Forzar sincronización de una entidad",
)
async def force_sync(
    entity_type: str,
    entity_id: str,
    current_user: User = Depends(get_current_user),
):
    """Placeholder — forzar push/pull de una entidad específica."""
    return {
        "message": f"Forzar sync para {entity_type}/{entity_id} encolado",
        "entity_type": entity_type,
        "entity_id": entity_id,
    }


@router.post(
    "/telegram-webhook",
    summary="Webhook de Telegram (placeholder)",
)
async def telegram_webhook(request: Request):
    """Placeholder para webhook de Telegram Bot API."""
    return {"status": "received"}
