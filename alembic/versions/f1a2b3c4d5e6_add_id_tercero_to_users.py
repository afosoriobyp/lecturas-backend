"""add id_tercero to users

Revision ID: f1a2b3c4d5e6
Revises: aefcc82317c6
Create Date: 2026-05-30T12:00:00

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f1a2b3c4d5e6"
down_revision: Union[str, None] = "c27c167cc18a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("id_tercero", sa.String(50), nullable=True, index=True),
    )


def downgrade() -> None:
    op.drop_column("users", "id_tercero")
