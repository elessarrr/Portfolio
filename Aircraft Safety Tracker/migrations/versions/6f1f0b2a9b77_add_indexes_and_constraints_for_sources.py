"""add_indexes_and_constraints_for_sources

Revision ID: 6f1f0b2a9b77
Revises: 3a91c2c7d1e4
Create Date: 2026-03-29 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '6f1f0b2a9b77'
down_revision = '3a91c2c7d1e4'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('incident_source', schema=None) as batch_op:
            batch_op.create_index(
                'ix_incident_source_incident_id_source_name',
                ['incident_id', 'source_name'],
                unique=False,
            )
            batch_op.create_unique_constraint(
                'uq_incident_source_source_name_source_record_id',
                ['source_name', 'source_record_id'],
            )
        return

    op.create_index(
        'ix_incident_source_incident_id_source_name',
        'incident_source',
        ['incident_id', 'source_name'],
        unique=False,
    )

    op.create_unique_constraint(
        'uq_incident_source_source_name_source_record_id',
        'incident_source',
        ['source_name', 'source_record_id'],
    )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'sqlite':
        with op.batch_alter_table('incident_source', schema=None) as batch_op:
            batch_op.drop_constraint('uq_incident_source_source_name_source_record_id', type_='unique')
            batch_op.drop_index('ix_incident_source_incident_id_source_name')
        return

    op.drop_constraint('uq_incident_source_source_name_source_record_id', 'incident_source', type_='unique')
    op.drop_index('ix_incident_source_incident_id_source_name', table_name='incident_source')
