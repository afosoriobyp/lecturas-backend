from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    accion: str,
    entidad_tipo: str,
    entidad_id: UUID | str | None = None,
    actor_id: str | None = None,
    detalle: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> AuditLog:
    """Registro centralizado de auditoría."""
    log = AuditLog(
        actor_id=actor_id,
        accion=accion,
        entidad_tipo=entidad_tipo,
        entidad_id=str(entidad_id) if entidad_id else None,
        detalle=detalle or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    await db.flush()
    return log
