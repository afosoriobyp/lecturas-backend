from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select

from app.api.dependencies import SessionDep
from app.core.security import require_roles
from app.models.audit_log import AuditLog
from app.models.sync_job import SyncJob
from app.models.user import User
from app.schemas.audit import AuditLogOut
from app.schemas.sync_job import SyncJobOut

router = APIRouter(prefix="/audit", tags=["Auditoría"])


@router.get(
    "/logs",
    response_model=list[AuditLogOut],
    summary="Listar logs de auditoría (solo admin/supervisor)",
)
async def list_audit_logs(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor")),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    accion: str | None = Query(None),
    entidad_tipo: str | None = Query(None),
    actor_id: UUID | None = Query(None),
    desde: datetime | None = Query(None),
    hasta: datetime | None = Query(None),
):
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())

    if accion:
        query = query.where(AuditLog.accion == accion)
    if entidad_tipo:
        query = query.where(AuditLog.entidad_tipo == entidad_tipo)
    if actor_id:
        query = query.where(AuditLog.actor_id == actor_id)
    if desde:
        query = query.where(AuditLog.timestamp >= desde)
    if hasta:
        query = query.where(AuditLog.timestamp <= hasta)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())


@router.get(
    "/sync-logs",
    response_model=list[SyncJobOut],
    summary="Listar registros de sincronización offline→online",
)
async def list_sync_logs(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor", "auditor")),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    estado: str | None = Query(None),
    tipo: str | None = Query(None),
):
    query = select(SyncJob).order_by(SyncJob.created_at.desc())

    if estado:
        query = query.where(SyncJob.estado == estado)
    if tipo:
        query = query.where(SyncJob.tipo == tipo)

    query = query.offset(skip).limit(limit)
    result = await session.execute(query)
    return list(result.scalars().all())
