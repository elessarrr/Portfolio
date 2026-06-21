"""add summary_generated_at to aircraft

Revision ID: a1b2c3d4e5f6
Revises: f6a7b8c9d0e1
Create Date: 2026-06-21

PRD 0012 — AI summary caching. Stores the timestamp of the last AI summary
generation so the app can serve a cached summary within the TTL window.
"""

import sqlalchemy as sa
from alembic import op


revision = "a1b2c3d4e5f6"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("aircraft") as batch_op:
        batch_op.add_column(sa.Column("summary_generated_at", sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table("aircraft") as batch_op:
        batch_op.drop_column("summary_generated_at")
