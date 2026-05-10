"""Add unique constraint for aircraft variants

Revision ID: 3f4c1b2a9d10
Revises: 9b3e7a1f4d2c
Create Date: 2026-03-22 22:20:00.000000

"""

from alembic import op


revision = '3f4c1b2a9d10'
down_revision = '9b3e7a1f4d2c'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('aircraft_variant', schema=None) as batch_op:
        batch_op.create_unique_constraint(
            'uq_aircraft_variant_aircraft_id_variant_name',
            ['aircraft_id', 'variant_name'],
        )


def downgrade():
    with op.batch_alter_table('aircraft_variant', schema=None) as batch_op:
        batch_op.drop_constraint('uq_aircraft_variant_aircraft_id_variant_name', type_='unique')

