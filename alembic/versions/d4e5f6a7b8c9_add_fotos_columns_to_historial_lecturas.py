"""add fotos columns to historial_lecturas

Revision ID: d4e5f6a7b8c9
Revises: f1a2b3c4d5e6
Create Date: 2026-06-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, None] = 'b15463a1d7c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('historial_lecturas', sa.Column('fotos', sa.Text(), nullable=True))
    op.add_column('historial_lecturas', sa.Column('fotos_pendientes', sa.Integer(), server_default='0', nullable=True))


def downgrade() -> None:
    op.drop_column('historial_lecturas', 'fotos_pendientes')
    op.drop_column('historial_lecturas', 'fotos')
