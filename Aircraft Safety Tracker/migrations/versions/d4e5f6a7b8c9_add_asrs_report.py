"""add asrs_report table for ASRS contributing factors layer

Revision ID: d4e5f6a7b8c9
Revises: c8f1a2b3d4e5
Create Date: 2026-06-18
"""

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c8f1a2b3d4e5"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "asrs_report",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("acn", sa.String(length=32), nullable=False),
        sa.Column("aircraft_make_model_raw", sa.String(length=128), nullable=True),
        sa.Column("primary_problem", sa.String(length=256), nullable=True),
        sa.Column("contributing_factors", sa.Text(), nullable=True),
        sa.Column("phase_of_flight", sa.String(length=128), nullable=True),
        sa.Column("report_year", sa.Integer(), nullable=True),
        sa.Column("synopsis", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("imported_at", sa.DateTime(), nullable=False),
        sa.Column("aircraft_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["aircraft_id"], ["aircraft.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("acn"),
    )
    op.create_index(op.f("ix_asrs_report_acn"), "asrs_report", ["acn"], unique=True)
    op.create_index(op.f("ix_asrs_report_aircraft_id"), "asrs_report", ["aircraft_id"], unique=False)
    op.create_index(
        op.f("ix_asrs_report_aircraft_make_model_raw"),
        "asrs_report",
        ["aircraft_make_model_raw"],
        unique=False,
    )
    op.create_index(op.f("ix_asrs_report_report_year"), "asrs_report", ["report_year"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_asrs_report_report_year"), table_name="asrs_report")
    op.drop_index(op.f("ix_asrs_report_aircraft_make_model_raw"), table_name="asrs_report")
    op.drop_index(op.f("ix_asrs_report_aircraft_id"), table_name="asrs_report")
    op.drop_index(op.f("ix_asrs_report_acn"), table_name="asrs_report")
    op.drop_table("asrs_report")
