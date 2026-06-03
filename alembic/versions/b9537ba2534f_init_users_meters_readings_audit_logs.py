"""init: users, meters, readings, audit_logs

Revision ID: b9537ba2534f
Revises:
Create Date: 2026-05-27T14:01:36

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b9537ba2534f"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("username", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("email", sa.String(255), unique=True, nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("rol", sa.String(50), server_default="lector", nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("telegram_id", sa.BigInteger(), unique=True, nullable=True, index=True),
        sa.Column("telegram_username", sa.String(100), nullable=True),
        sa.Column("telegram_chat_id", sa.BigInteger(), nullable=True),
    )

    # --- meters ---
    op.create_table(
        "meters",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("estado_sync", sa.String(50), server_default="pending", nullable=False, index=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("codigo_medidor", sa.String(50), unique=True, nullable=False, index=True),
        sa.Column("direccion", sa.Text(), nullable=True),
        sa.Column("latitud", sa.Float(), nullable=True),
        sa.Column("longitud", sa.Float(), nullable=True),
        sa.Column("gps_json", postgresql.JSON, nullable=True),
        sa.Column("estado", sa.String(50), server_default="activo", nullable=False),
        sa.Column("tipo", sa.String(50), nullable=True),
        sa.Column("lector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
    )

    # --- readings ---
    op.create_table(
        "readings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("estado_sync", sa.String(50), server_default="pending", nullable=False, index=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("lectura_anterior", sa.Float(), nullable=True),
        sa.Column("lectura_actual", sa.Float(), nullable=False),
        sa.Column("consumo", sa.Float(), nullable=True),
        sa.Column("fecha_lectura", sa.Date(), nullable=False, index=True),
        sa.Column("foto_url", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("gps_json", postgresql.JSON, nullable=True),
        sa.Column("metodo_captura", sa.String(50), server_default="manual", nullable=False),
        sa.Column("meter_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("meters.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("lector_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True),
    )

    # --- audit_logs ---
    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"), index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, index=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("accion", sa.String(100), nullable=False, index=True),
        sa.Column("entidad_tipo", sa.String(50), nullable=True),
        sa.Column("entidad_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("detalle", postgresql.JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("readings")
    op.drop_table("meters")
    op.drop_table("users")
