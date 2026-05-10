"""add is_active soft-flag to incident_source

Revision ID: f4a9c2d1e7b3
Revises: a1b2c3d4e5f6, c1f9a2b7d4e6
Create Date: 2026-04-26
"""

from alembic import op
import sqlalchemy as sa


revision = 'f4a9c2d1e7b3'
down_revision = ('a1b2c3d4e5f6', 'c1f9a2b7d4e6')
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('incident_source', schema=None) as batch_op:
        batch_op.add_column(
            sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true())
        )


def downgrade():
    with op.batch_alter_table('incident_source', schema=None) as batch_op:
        batch_op.drop_column('is_active')
