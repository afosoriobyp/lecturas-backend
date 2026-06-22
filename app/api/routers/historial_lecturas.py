from __future__ import annotations

import csv
import io
import json
import os
from datetime import date
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException, Response
from sqlalchemy import cast, delete, func, Integer, select, text

from app.api.dependencies import SessionDep
from app.core.config import settings
from app.core.exceptions import ForbiddenException, NotFoundException
from app.core.security import get_current_user, require_roles
from app.models.historial_lectura import HistorialLectura
from app.models.no_read_reason import NoReadReason
from app.models.user import User
from app.schemas.historial_lectura import HistorialLecturaListOut, HistorialLecturaOut, HistorialLecturaUpdate
from app.services.audit import log_action

router = APIRouter(prefix="/historial-lecturas", tags=["Historial Lecturas"])


def validar_consumo(consumo: float, promedio: float | None,
                     consumo_1: float | None = None,
                     consumo_2: float | None = None,
                     consumo_3: float | None = None) -> dict:
    if consumo <= 0:
        return {"categoria": "Girado Sentido Contrario", "porcentaje": 0}
    promedio_efectivo = promedio
    if not promedio_efectivo or promedio_efectivo <= 0:
        historicos = [c for c in (consumo_1, consumo_2, consumo_3) if c is not None and c > 0]
        if historicos:
            promedio_efectivo = sum(historicos) / len(historicos)
    if not promedio_efectivo or promedio_efectivo <= 0:
        return {"categoria": None, "porcentaje": None}
    pct = (consumo / promedio_efectivo) * 100
    if pct <= 50:
        return {"categoria": "Consumo Bajo", "porcentaje": round(pct, 2)}
    elif pct <= 100:
        return {"categoria": "Consumo Normal", "porcentaje": round(pct, 2)}
    elif pct <= 150:
        return {"categoria": "Consumo Alto", "porcentaje": round(pct, 2)}
    else:
        return {"categoria": "Consumo Elevado", "porcentaje": round(pct, 2)}


@router.get("/", response_model=HistorialLecturaListOut)
async def list_historial_lecturas(
    session: SessionDep,
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=5000),
    nuis: str | None = Query(None, description="Buscar por NIUS/medidor (búsqueda parcial)"),
    ruta_lectura: str | None = Query(None),
    nom_suscriptor: str | None = Query(None),
    serial_medidor: str | None = Query(None, description="Buscar por serial/número de medidor (búsqueda parcial)"),
    id_predio: str | None = Query(None, description="Buscar por ID de predio (búsqueda parcial)"),
):
    count_query = select(func.count(HistorialLectura.id_lectura))
    data_query = select(HistorialLectura)

    if current_user.rol == "lector" and current_user.id_tercero:
        count_query = count_query.where(HistorialLectura.id_tercero == current_user.id_tercero)
        data_query = data_query.where(HistorialLectura.id_tercero == current_user.id_tercero)

    if nuis:
        count_query = count_query.where(HistorialLectura.nuis.ilike(f"%{nuis}%"))
        data_query = data_query.where(HistorialLectura.nuis.ilike(f"%{nuis}%"))
    if id_predio:
        count_query = count_query.where(HistorialLectura.id_predio.ilike(f"%{id_predio}%"))
        data_query = data_query.where(HistorialLectura.id_predio.ilike(f"%{id_predio}%"))
    if ruta_lectura:
        count_query = count_query.where(HistorialLectura.ruta_lectura == ruta_lectura)
        data_query = data_query.where(HistorialLectura.ruta_lectura == ruta_lectura)
    if nom_suscriptor:
        count_query = count_query.where(HistorialLectura.nom_suscriptor.ilike(f"%{nom_suscriptor}%"))
        data_query = data_query.where(HistorialLectura.nom_suscriptor.ilike(f"%{nom_suscriptor}%"))
    if serial_medidor:
        count_query = count_query.where(HistorialLectura.serial_medidor.ilike(f"%{serial_medidor}%"))
        data_query = data_query.where(HistorialLectura.serial_medidor.ilike(f"%{serial_medidor}%"))

    total_result = await session.execute(count_query)
    total = total_result.scalar() or 0

    data_query = data_query.order_by(cast(HistorialLectura.orden_lectura, Integer)).offset(skip).limit(limit)
    result = await session.execute(data_query)
    items = list(result.scalars().all())

    for item in items:
        if item.consumo is not None:
            v = validar_consumo(item.consumo, item.promedio,
                                consumo_1=item.consumo_1,
                                consumo_2=item.consumo_2,
                                consumo_3=item.consumo_3)
            item.consumo_categoria = v.get("categoria")
            item.consumo_porcentaje = v.get("porcentaje")

    return HistorialLecturaListOut(total=total, items=items)


CSV_HEADERS = [
    "LECTURA_ANT", "LECTURA", "CONSUMO", "SOLUCION_CONSUMO", "PROMEDIO",
    "ID_NOVEDAD", "NOM_SUSCRIPTOR", "SERIAL_MEDIDOR", "NOM_MARCA",
    "ID_CICLO", "ORDEN_LECTURA", "RUTA_LECTURA",
    "CONSUMO_1", "CONSUMO_2", "CONSUMO_3",
]

COLUMN_MAP = {
    "LECTURA_ANT": "lectura_ant",
    "LECTURA": "lectura",
    "CONSUMO": "consumo",
    "SOLUCION_CONSUMO": "solucion_consumo",
    "PROMEDIO": "promedio",
    "ID_NOVEDAD": "id_novedad",
    "NOM_SUSCRIPTOR": "nom_suscriptor",
    "SERIAL_MEDIDOR": "serial_medidor",
    "NOM_MARCA": "nom_marca",
    "ID_CICLO": "id_ciclo",
    "ORDEN_LECTURA": "orden_lectura",
    "RUTA_LECTURA": "ruta_lectura",
    "CONSUMO_1": "consumo_1",
    "CONSUMO_2": "consumo_2",
    "CONSUMO_3": "consumo_3",
}

LOOKUP_FIELDS = ["ID_CICLO", "ORDEN_LECTURA", "RUTA_LECTURA"]

IMPORT_COLUMNS = ["LECTURA", "CONSUMO", "SOLUCION_CONSUMO", "ID_NOVEDAD"]


EXPORT_COLUMNS = [
    "id_lectura", "nom_aps", "nom_ciudad", "id_tercero", "nom_lector",
    "id_predio", "nuis", "nom_barrio", "direccion", "fecha",
    "lectura_ant", "lectura", "consumo", "solucion_consumo", "promedio",
    "id_novedad", "nom_suscriptor", "serial_medidor", "nom_marca",
    "id_ciclo", "orden_lectura", "ruta_lectura",
    "consumo_1", "consumo_2", "consumo_3",
    "status", "observacion", "fotos", "fotos_pendientes",
]


def _generate_csv(rows: list[HistorialLectura]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(EXPORT_COLUMNS)
    for r in rows:
        writer.writerow([getattr(r, col) for col in EXPORT_COLUMNS])
    return output.getvalue()


def _generate_xlsx(rows: list[HistorialLectura]) -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Historial Lecturas"
    ws.append(EXPORT_COLUMNS)
    for r in rows:
        ws.append([getattr(r, col) for col in EXPORT_COLUMNS])
    output = io.BytesIO()
    wb.save(output)
    return output.getvalue()


@router.get("/export")
async def export_historial_lecturas(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "auditor")),
    formato: str = Query(pattern=r"^(csv|xlsx)$"),
    nuis: str | None = Query(None),
    nom_suscriptor: str | None = Query(None),
    serial_medidor: str | None = Query(None, description="Buscar por serial/número de medidor (búsqueda parcial)"),
):
    query = select(HistorialLectura)

    if nuis:
        query = query.where(HistorialLectura.nuis.ilike(f"%{nuis}%"))
    if nom_suscriptor:
        query = query.where(HistorialLectura.nom_suscriptor.ilike(f"%{nom_suscriptor}%"))
    if serial_medidor:
        query = query.where(HistorialLectura.serial_medidor.ilike(f"%{serial_medidor}%"))

    query = query.order_by(cast(HistorialLectura.orden_lectura, Integer))
    result = await session.execute(query)
    rows = list(result.scalars().all())

    today = date.today().isoformat()

    if formato == "csv":
        content = _generate_csv(rows)
        media_type = "text/csv"
        filename = f"historial-lecturas-{today}.csv"
    else:
        content = _generate_xlsx(rows)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = f"historial-lecturas-{today}.xlsx"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.patch("/{id_lectura}", response_model=HistorialLecturaOut)
async def update_historial_lectura(
    session: SessionDep,
    id_lectura: str,
    payload: HistorialLecturaUpdate,
    current_user: User = Depends(get_current_user),
):
    if current_user.rol not in ("lector", "admin", "supervisor"):
        raise ForbiddenException("No autorizado")

    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")

    update_data: dict[str, object] = {}

    if payload.lectura is not None:
        update_data["lectura"] = payload.lectura
        lectura_ant = historial.lectura_ant or 0
        update_data["consumo"] = payload.lectura - lectura_ant
    elif payload.consumo is not None:
        update_data["consumo"] = payload.consumo

    if payload.id_novedad is not None and payload.id_novedad != "":
        update_data["id_novedad"] = payload.id_novedad
        motivo_result = await session.execute(
            text("SELECT sugiere_promedio FROM no_read_reasons WHERE codigo = CAST(:codigo AS integer)"),
            {"codigo": int(payload.id_novedad)},
        )
        row = motivo_result.one_or_none()
        if row:
            update_data["solucion_consumo"] = (
                "POR PROMEDIO" if row.sugiere_promedio.strip().upper() == "S" else "POR DIFERENCIA"
            )
    elif payload.id_novedad == "" and payload.solucion_consumo is None:
        update_data["id_novedad"] = None
        update_data["solucion_consumo"] = None

    if payload.solucion_consumo is not None:
        update_data["solucion_consumo"] = payload.solucion_consumo

    if payload.status is not None:
        update_data["status"] = payload.status

    if payload.observacion is not None:
        update_data["observacion"] = payload.observacion

    if payload.fecha is not None:
        update_data["fecha"] = payload.fecha

    if payload.fotos is not None:
        update_data["fotos"] = json.dumps(payload.fotos)

    if payload.fotos_pendientes is not None:
        update_data["fotos_pendientes"] = payload.fotos_pendientes

    for key, value in update_data.items():
        setattr(historial, key, value)

    await session.flush()
    await session.refresh(historial)

    consumo = historial.consumo
    promedio = historial.promedio
    validacion = {}
    if consumo is not None:
        validacion = validar_consumo(consumo, promedio,
                                     consumo_1=historial.consumo_1,
                                     consumo_2=historial.consumo_2,
                                     consumo_3=historial.consumo_3)

    await log_action(
        session, accion="historial_lectura.update", entidad_tipo="historial_lectura",
        entidad_id=id_lectura, actor_id=str(current_user.id),
        detalle={k: str(v) for k, v in update_data.items()},
    )

    if validacion.get("categoria"):
        await log_action(
            session, accion="historial_lectura.validation", entidad_tipo="historial_lectura",
            entidad_id=id_lectura, actor_id=str(current_user.id),
            detalle={
                "categoria": validacion["categoria"],
                "porcentaje": validacion.get("porcentaje"),
                "consumo": consumo,
                "promedio": promedio,
                "version_app": "1.0.0",
            },
        )

    historial.consumo_categoria = validacion.get("categoria")
    historial.consumo_porcentaje = validacion.get("porcentaje")

    return historial


@router.get("/{id_lectura}", response_model=HistorialLecturaOut)
async def get_historial_lectura(
    session: SessionDep,
    id_lectura: str,
    current_user: User = Depends(get_current_user),
):
    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")

    if historial.consumo is not None:
        validacion = validar_consumo(historial.consumo, historial.promedio,
                                     consumo_1=historial.consumo_1,
                                     consumo_2=historial.consumo_2,
                                     consumo_3=historial.consumo_3)
        historial.consumo_categoria = validacion.get("categoria")
        historial.consumo_porcentaje = validacion.get("porcentaje")

    return historial


@router.post("/{id_lectura}/fotos", response_model=dict)
async def upload_fotos(
    id_lectura: str,
    session: SessionDep,
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),
):
    if current_user.rol not in ("lector", "admin", "supervisor"):
        raise ForbiddenException("No autorizado")

    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")

    if len(files) > settings.MAX_FOTOS_PER_LECTURA:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {settings.MAX_FOTOS_PER_LECTURA} fotos permitidas",
        )

    existing_fotos: list[str] = []
    if historial.fotos:
        try:
            existing_fotos = json.loads(historial.fotos)
        except (json.JSONDecodeError, TypeError):
            existing_fotos = []

    total_fotos = len(existing_fotos) + len(files)
    if total_fotos > settings.MAX_FOTOS_PER_LECTURA:
        raise HTTPException(
            status_code=400,
            detail=f"Máximo {settings.MAX_FOTOS_PER_LECTURA} fotos permitidas. Ya tienes {len(existing_fotos)}.",
        )

    for file in files:
        if file.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Tipo de archivo no permitido: {file.content_type}. Permitidos: {settings.ALLOWED_IMAGE_TYPES}",
            )

        content = await file.read()
        if len(content) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Archivo muy grande. Máximo {settings.MAX_IMAGE_SIZE_MB}MB",
            )

    id_predio = historial.id_predio or "sin_predio"
    upload_dir = Path(settings.UPLOAD_DIR) / "historial-lecturas" / id_predio
    upload_dir.mkdir(parents=True, exist_ok=True)

    next_index = len(existing_fotos) + 1
    new_fotos = []

    for file in files:
        ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else "jpg"
        filename = f"{id_predio}_{next_index}.{ext}"
        filepath = upload_dir / filename

        with open(filepath, "wb") as f:
            f.write(await file.read())

        new_fotos.append(filename)
        next_index += 1

    all_fotos = existing_fotos + new_fotos
    historial.fotos = json.dumps(all_fotos)
    historial.fotos_pendientes = 0

    await session.flush()

    await log_action(
        session,
        accion="historial_lectura.upload_fotos",
        entidad_tipo="historial_lectura",
        entidad_id=id_lectura,
        actor_id=str(current_user.id),
        detalle={"fotos_subidas": len(new_fotos), "total_fotos": len(all_fotos)},
    )

    return {"fotos": all_fotos}


@router.delete("/{id_lectura}/fotos", response_model=dict)
async def delete_fotos(
    id_lectura: str,
    session: SessionDep,
    filenames: str = Query(..., description="Comma-separated list of filenames to delete"),
    current_user: User = Depends(get_current_user),
):
    if current_user.rol not in ("lector", "admin", "supervisor"):
        raise ForbiddenException("No autorizado")

    result = await session.execute(
        select(HistorialLectura).where(HistorialLectura.id_lectura == id_lectura)
    )
    historial = result.scalar_one_or_none()
    if not historial:
        raise NotFoundException("HistorialLectura")

    if not historial.fotos:
        raise HTTPException(status_code=404, detail="No hay fotos para eliminar")

    try:
        existing_fotos: list[str] = json.loads(historial.fotos)
    except (json.JSONDecodeError, TypeError):
        raise HTTPException(status_code=500, detail="Error al leer las fotos almacenadas")

    files_to_delete = [f.strip() for f in filenames.split(",") if f.strip()]
    remaining_fotos = [f for f in existing_fotos if f not in files_to_delete]

    id_predio = historial.id_predio or "sin_predio"
    upload_dir = Path(settings.UPLOAD_DIR) / "historial-lecturas" / id_predio

    for filename in files_to_delete:
        filepath = upload_dir / filename
        if filepath.exists():
            filepath.unlink()

    reindexed_fotos = []
    for idx, foto in enumerate(remaining_fotos, start=1):
        ext = foto.rsplit(".", 1)[-1] if "." in foto else "jpg"
        new_filename = f"{id_predio}_{idx}.{ext}"
        old_filepath = upload_dir / foto
        new_filepath = upload_dir / new_filename

        if old_filepath.exists() and old_filepath != new_filepath:
            old_filepath.rename(new_filepath)

        reindexed_fotos.append(new_filename)

    historial.fotos = json.dumps(reindexed_fotos)

    await session.flush()

    await log_action(
        session,
        accion="historial_lectura.delete_fotos",
        entidad_tipo="historial_lectura",
        entidad_id=id_lectura,
        actor_id=str(current_user.id),
        detalle={"fotos_eliminadas": len(files_to_delete), "total_fotos": len(reindexed_fotos)},
    )

    return {"fotos": reindexed_fotos}


@router.post("/import")
async def import_historial_lecturas_csv(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor")),
    file: UploadFile = File(...),
):
    if not file.filename or not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="El archivo debe tener extensión .csv")

    content = await file.read()
    try:
        decoded = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        decoded = content.decode("latin-1")

    first_line = decoded.splitlines()[0] if decoded.splitlines() else ""
    delimiter = ";" if ";" in first_line else ","
    reader = csv.DictReader(io.StringIO(decoded), delimiter=delimiter)
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV vacío o sin encabezados")

    from datetime import date as date_type

    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    model_cols = {c.name for c in HistorialLectura.__table__.columns}
    float_cols = {"lectura_ant", "lectura", "consumo", "promedio", "consumo_1", "consumo_2", "consumo_3"}

    await session.execute(delete(HistorialLectura))

    creados = 0
    errores = 0
    detalles: list[str] = []

    for idx, row in enumerate(rows, start=1):
        try:
            id_lectura_val = row.get("id_lectura", "").strip()
            if not id_lectura_val:
                raise ValueError("'id_lectura' es requerido")
            data: dict[str, object] = {"id_lectura": id_lectura_val}
            for header in reader.fieldnames:
                key = header.strip()
                if key not in model_cols:
                    continue
                val = row.get(header, "").strip()
                if not val:
                    data[key] = None
                elif key in float_cols:
                    try:
                        data[key] = float(val)
                    except ValueError:
                        raise ValueError(f"'{header}' debe ser un valor numérico")
                elif key == "fecha":
                    try:
                        data[key] = date_type.fromisoformat(val)
                    except ValueError:
                        raise ValueError(f"'{header}' debe ser fecha ISO (YYYY-MM-DD)")
                else:
                    data[key] = val

            historial = HistorialLectura(**data)
            session.add(historial)
            creados += 1

        except Exception as exc:
            errores += 1
            detalles.append(f"fila {idx}: {exc}")

    if creados > 0:
        await session.flush()
        await log_action(
            session,
            accion="historial_lectura.import_csv",
            entidad_tipo="historial_lectura",
            actor_id=str(current_user.id),
            detalle={"creados": creados, "errores": errores, "total": len(rows)},
        )

    return {"creados": creados, "errores": errores, "total": len(rows), "detalles": detalles}


@router.delete("/all")
async def delete_all_historial_lecturas(
    session: SessionDep,
    current_user: User = Depends(require_roles("admin", "supervisor")),
):
    result = await session.execute(select(HistorialLectura).limit(1))
    if result.first() is None:
        return {"eliminados": 0, "message": "No hay registros para eliminar"}

    result = await session.execute(delete(HistorialLectura))
    count = result.rowcount

    await log_action(
        session,
        accion="historial_lectura.delete_all",
        entidad_tipo="historial_lectura",
        actor_id=str(current_user.id),
        detalle={"eliminados": count},
    )

    return {"eliminados": count, "message": f"Se eliminaron {count} registros"}
