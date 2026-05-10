"""Add foreign key indexes for V2 models

Revision ID: 9b3e7a1f4d2c
Revises: be4e7bb8751a
Create Date: 2026-03-22 16:15:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = '9b3e7a1f4d2c'
down_revision = 'be4e7bb8751a'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_incident_aircraft_id'), ['aircraft_id'], unique=False)

    with op.batch_alter_table('aircraft_variant', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_aircraft_variant_aircraft_id'), ['aircraft_id'], unique=False)

    with op.batch_alter_table('incident_source', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_incident_source_incident_id'), ['incident_id'], unique=False)

    with op.batch_alter_table('system_tag', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_system_tag_incident_id'), ['incident_id'], unique=False)

    with op.batch_alter_table('report_analysis', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_report_analysis_incident_id'), ['incident_id'], unique=False)


def downgrade():
    with op.batch_alter_table('report_analysis', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_report_analysis_incident_id'))

    with op.batch_alter_table('system_tag', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_system_tag_incident_id'))

    with op.batch_alter_table('incident_source', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_incident_source_incident_id'))

    with op.batch_alter_table('aircraft_variant', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_aircraft_variant_aircraft_id'))

    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_incident_aircraft_id'))
