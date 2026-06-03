from __future__ import annotations

import csv
import io
from datetime import date, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.api.dependencies import SessionDep
from app.core.security import get_current_user, require_roles
from app.models.meter import Meter
from app.models.no_read_reason import NoReadReason
from app.models.reading import Reading
from app.models.user import User

router = APIRouter(
    prefix="/export",
    tags=["Exportación"],
)


def _build_readings_query(
    lector_id: UUID | None,
    fecha_desde: date | None,
    fecha_hasta: date | None,
):
    query = (
        select(Reading)
        .options(
            joinedload(Reading.meter),
            joinedload(Reading.lector),
            joinedload(Reading.motivo_no_lectura),
        )
    )
    if lector_id:
        query = query.where(Reading.lector_id == lector_id)
    if fecha_desde:
        query = query.where(Reading.fecha_lectura >= fecha_desde)
    if fecha_hasta:
        query = query.where(Reading.fecha_lectura <= fecha_hasta)
    return query.order_by(Reading.fecha_lectura.desc(), Reading.created_at.desc())


def _reading_rows(readings: list[Reading]) -> list[dict]:
    return [
        {
            "ID": str(r.id),
            "Medidor": r.meter.codigo_medidor if r.meter else "",
            "Lector": r.lector.username if r.lector else "",
            "Fecha Lectura": str(r.fecha_lectura),
            "Lectura Anterior": r.lectura_anterior,
            "Lectura Actual": r.lectura_actual,
            "Consumo": r.consumo,
            "Metodo": r.metodo_captura,
            "Estado Validacion": r.estado_validacion,
            "Estado Sync": r.estado_sync,
            "Motivo No Lectura": r.motivo_no_lectura.codigo if r.motivo_no_lectura else "",
            "Observaciones": r.observaciones or "",
            "Creado": str(r.created_at),
        }
        for r in readings
    ]


def _generate_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    if not rows:
        return ""
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def _generate_xlsx(rows: list[dict]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Lecturas"
    if not rows:
        wb.save(io.BytesIO())
        return io.BytesIO().getvalue()

    headers = list(rows[0].keys())
    ws.append(headers)
    for row in rows:
        ws.append([row[h] for h in headers])

    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


@router.get("/lecturas")
async def export_lecturas(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    formato: str = Query("csv", pattern=r"^(csv|xlsx)$"),
    lector_id: UUID | None = None,
    fecha_desde: date | None = None,
    fecha_hasta: date | None = None,
):
    if current_user.rol == "lector":
        lector_id = current_user.id

    query = _build_readings_query(lector_id, fecha_desde, fecha_hasta)
    result = await session.execute(query)
    readings = list(result.unique().scalars().all())
    rows = _reading_rows(readings)

    if formato == "csv":
        content = _generate_csv(rows)
        media_type = "text/csv"
        filename = f"lecturas_{date.today()}.csv"
    else:
        content = _generate_xlsx(rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"lecturas_{date.today()}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reporte-global")
async def export_reporte_global(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor")),
    fecha_desde: date | None = Query(None, alias="fechaInicio"),
    fecha_hasta: date | None = Query(None, alias="fechaFin"),
):
    query = (
        select(Reading)
        .options(
            joinedload(Reading.meter),
            joinedload(Reading.lector),
            joinedload(Reading.motivo_no_lectura),
        )
    )
    if fecha_desde:
        query = query.where(Reading.fecha_lectura >= fecha_desde)
    if fecha_hasta:
        query = query.where(Reading.fecha_lectura <= fecha_hasta)
    query = query.order_by(Reading.fecha_lectura.desc(), Reading.created_at.desc())

    result = await session.execute(query)
    readings = list(result.unique().scalars().all())
    rows = _reading_rows(readings)

    xlsx_bytes = _generate_xlsx(rows)
    return Response(
        content=xlsx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="reporte_global_{date.today()}.xlsx"'
        },
    )
