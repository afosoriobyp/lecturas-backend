"""rename historial_lecturas columns to lowercase

Revision ID: c27c167cc18a
Revises: cf1a687afa01
Create Date: 2026-05-28 22:35:04.014091

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c27c167cc18a'
down_revision: Union[str, None] = 'cf1a687afa01'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

RENAME_MAP = {
    "ID_LECTURA": "id_lectura",
    "NOM_APS": "nom_aps",
    "NOM_CIUDAD": "nom_ciudad",
    "ID_TERCERO": "id_tercero",
    "NOM_LECTOR": "nom_lector",
    "ID_PREDIO": "id_predio",
    "NUIS": "nuis",
    "NOM_BARRIO": "nom_barrio",
    "DIRECCION": "direccion",
    "FECHA": "fecha",
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


def upgrade() -> None:
    for old, new in RENAME_MAP.items():
        op.alter_column("historial_lecturas", old, new_column_name=new)


def downgrade() -> None:
    for old, new in RENAME_MAP.items():
        op.alter_column("historial_lecturas", new, new_column_name=old)
