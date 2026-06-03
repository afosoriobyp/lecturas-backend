"""create historial_lecturas table

Revision ID: cf1a687afa01
Revises: aefcc82317c6
Create Date: 2026-05-28 22:01:46.315700

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cf1a687afa01'
down_revision: Union[str, None] = 'aefcc82317c6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('historial_lecturas',
        sa.Column('ID_LECTURA', sa.String(length=50), nullable=False),
        sa.Column('NOM_APS', sa.Text(), nullable=True),
        sa.Column('NOM_CIUDAD', sa.Text(), nullable=True),
        sa.Column('ID_TERCERO', sa.String(length=50), nullable=True),
        sa.Column('NOM_LECTOR', sa.Text(), nullable=True),
        sa.Column('ID_PREDIO', sa.String(length=50), nullable=True),
        sa.Column('NUIS', sa.String(length=50), nullable=True),
        sa.Column('NOM_BARRIO', sa.Text(), nullable=True),
        sa.Column('DIRECCION', sa.Text(), nullable=True),
        sa.Column('FECHA', sa.Date(), nullable=True),
        sa.Column('LECTURA_ANT', sa.Float(), nullable=True),
        sa.Column('LECTURA', sa.Float(), nullable=True),
        sa.Column('CONSUMO', sa.Float(), nullable=True),
        sa.Column('SOLUCION_CONSUMO', sa.String(length=100), nullable=True),
        sa.Column('PROMEDIO', sa.Float(), nullable=True),
        sa.Column('ID_NOVEDAD', sa.String(length=50), nullable=True),
        sa.Column('NOM_SUSCRIPTOR', sa.Text(), nullable=True),
        sa.Column('SERIAL_MEDIDOR', sa.String(length=100), nullable=True),
        sa.Column('NOM_MARCA', sa.Text(), nullable=True),
        sa.Column('ID_CICLO', sa.String(length=50), nullable=True),
        sa.Column('ORDEN_LECTURA', sa.String(length=50), nullable=True),
        sa.Column('RUTA_LECTURA', sa.String(length=100), nullable=True),
        sa.Column('CONSUMO_1', sa.Float(), nullable=True),
        sa.Column('CONSUMO_2', sa.Float(), nullable=True),
        sa.Column('CONSUMO_3', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('ID_LECTURA'),
    )
    op.create_index(op.f('ix_historial_lecturas_ID_LECTURA'), 'historial_lecturas', ['ID_LECTURA'], unique=True)
    op.create_index(op.f('ix_historial_lecturas_ID_PREDIO'), 'historial_lecturas', ['ID_PREDIO'], unique=False)
    op.create_index(op.f('ix_historial_lecturas_NUIS'), 'historial_lecturas', ['NUIS'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_historial_lecturas_NUIS'), table_name='historial_lecturas')
    op.drop_index(op.f('ix_historial_lecturas_ID_PREDIO'), table_name='historial_lecturas')
    op.drop_index(op.f('ix_historial_lecturas_ID_LECTURA'), table_name='historial_lecturas')
    op.drop_table('historial_lecturas')
