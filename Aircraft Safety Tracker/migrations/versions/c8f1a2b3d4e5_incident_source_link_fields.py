"""incident_source link fields for v3 import contract

Revision ID: c8f1a2b3d4e5
Revises: 18bd2eb49ebb
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa


revision = "c8f1a2b3d4e5"
down_revision = "18bd2eb49ebb"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("incident_source", schema=None) as batch_op:
        batch_op.add_column(sa.Column("source_record_id", sa.String(length=128), nullable=True))
        batch_op.add_column(
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true())
        )
        batch_op.create_index(
            batch_op.f("ix_incident_source_incident_id"),
            ["incident_id"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_incident_source_incident_id_source_name"),
            ["incident_id", "source_name"],
            unique=False,
        )
        batch_op.create_index(
            batch_op.f("ix_incident_source_source_record_id"),
            ["source_record_id"],
            unique=False,
        )
        batch_op.create_unique_constraint(
            "uq_incident_source_source_name_source_record_id",
            ["source_name", "source_record_id"],
        )


def downgrade():
    with op.batch_alter_table("incident_source", schema=None) as batch_op:
        batch_op.drop_constraint("uq_incident_source_source_name_source_record_id", type_="unique")
        batch_op.drop_index(batch_op.f("ix_incident_source_source_record_id"))
        batch_op.drop_index(batch_op.f("ix_incident_source_incident_id_source_name"))
        batch_op.drop_index(batch_op.f("ix_incident_source_incident_id"))
        batch_op.drop_column("is_active")
        batch_op.drop_column("source_record_id")
