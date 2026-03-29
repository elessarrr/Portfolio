"""Add variant_name to incident

Revision ID: 4c2f1a0d8e21
Revises: 3f4c1b2a9d10
Create Date: 2026-03-28 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '4c2f1a0d8e21'
down_revision = '3f4c1b2a9d10'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.add_column(sa.Column('variant_name', sa.String(length=64), nullable=True))
        batch_op.create_index(batch_op.f('ix_incident_variant_name'), ['variant_name'], unique=False)


def downgrade():
    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_incident_variant_name'))
        batch_op.drop_column('variant_name')

