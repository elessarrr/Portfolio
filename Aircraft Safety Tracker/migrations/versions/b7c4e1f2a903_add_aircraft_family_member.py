"""add aircraft_family_member table

Revision ID: b7c4e1f2a903
Revises: f4a9c2d1e7b3
Create Date: 2026-05-24
"""

from alembic import op
import sqlalchemy as sa


revision = "b7c4e1f2a903"
down_revision = ("f4a9c2d1e7b3", "c955648fb8e6")
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "aircraft_family_member",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("family_aircraft_id", sa.Integer(), nullable=False),
        sa.Column("member_aircraft_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["family_aircraft_id"], ["aircraft.id"]),
        sa.ForeignKeyConstraint(["member_aircraft_id"], ["aircraft.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "family_aircraft_id",
            "member_aircraft_id",
            name="uq_aircraft_family_member_family_member",
        ),
        sa.UniqueConstraint(
            "member_aircraft_id",
            name="uq_aircraft_family_member_member",
        ),
    )
    with op.batch_alter_table("aircraft_family_member", schema=None) as batch_op:
        batch_op.create_index(
            batch_op.f("ix_aircraft_family_member_family_aircraft_id"),
            ["family_aircraft_id"],
            unique=False,
        )


def downgrade():
    op.drop_table("aircraft_family_member")
