from __future__ import annotations

from contextvars import ContextVar
from typing import Any
from uuid import UUID

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from app.models.audit_log import AuditLog
from app.models.meter import Meter
from app.models.no_read_reason import NoReadReason
from app.models.reading import Reading
from app.models.ruta import Ruta
from app.models.ruta_asignada import RutaAsignada
from app.models.sync_job import SyncJob
from app.models.user import User

current_actor_id: ContextVar[str | None] = ContextVar("current_actor_id", default=None)
current_ip: ContextVar[str | None] = ContextVar("current_ip", default=None)
current_ua: ContextVar[str | None] = ContextVar("current_ua", default=None)

ENTITY_NAMES: dict[type, str] = {
    Meter: "meter",
    Reading: "reading",
    User: "user",
    NoReadReason: "no_read_reason",
    Ruta: "ruta",
    RutaAsignada: "ruta_asignada",
    SyncJob: "sync_job",
}

BUILTIN_ATTRS = {
    "id", "created_at", "updated_at", "estado_sync", "synced_at",
    "hashed_password", "telegram_id", "telegram_username", "telegram_chat_id",
    "cache_stats", "gps_json",
}


def _safe(val: Any) -> Any:
    if isinstance(val, UUID):
        return str(val)
    return val


def _summarize(instance: Any) -> dict[str, Any]:
    fields = {}
    for col in instance.__table__.columns:
        key = col.name
        if key in BUILTIN_ATTRS:
            continue
        val = getattr(instance, key, None)
        if val is not None:
            fields[key] = _safe(val)
    return fields


def _get_session(instance: Any) -> AsyncSession | None:
    return (
        AsyncSession.object_session(instance)
        if hasattr(instance, "_sa_instance_state")
        else None
    )


def _log(instance: Any, accion: str) -> None:
    actor_id = current_actor_id.get()
    if not actor_id:
        return

    session = _get_session(instance)
    if session is None:
        return

    entidad_tipo = ENTITY_NAMES.get(type(instance), "unknown")
    log = AuditLog(
        actor_id=actor_id,
        accion=accion,
        entidad_tipo=entidad_tipo,
        entidad_id=_safe(getattr(instance, "id", None)),
        detalle=_summarize(instance),
        ip_address=current_ip.get(),
        user_agent=current_ua.get(),
    )
    session.add(log)


def _after_insert(mapper: Any, connection: Any, target: Any) -> None:
    _log(target, f"{ENTITY_NAMES.get(type(target), 'unknown')}.create")


def _after_update(mapper: Any, connection: Any, target: Any) -> None:
    _log(target, f"{ENTITY_NAMES.get(type(target), 'unknown')}.update")


def _after_delete(mapper: Any, connection: Any, target: Any) -> None:
    _log(target, f"{ENTITY_NAMES.get(type(target), 'unknown')}.delete")


def register_audit_events() -> None:
    for model in ENTITY_NAMES:
        event.listen(model, "after_insert", _after_insert)
        event.listen(model, "after_update", _after_update)
        event.listen(model, "after_delete", _after_delete)
