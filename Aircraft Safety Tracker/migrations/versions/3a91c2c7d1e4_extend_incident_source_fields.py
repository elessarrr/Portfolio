"""extend_incident_source_fields

Revision ID: 3a91c2c7d1e4
Revises: 0f6d7d9c3f2a
Create Date: 2026-03-29 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '3a91c2c7d1e4'
down_revision = '0f6d7d9c3f2a'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('incident_source', sa.Column('source_record_id', sa.String(length=128), nullable=True))
    op.add_column('incident_source', sa.Column('confidence_level', sa.String(length=32), nullable=True, server_default='Unverified'))
    op.create_index(op.f('ix_incident_source_source_record_id'), 'incident_source', ['source_record_id'], unique=False)

    op.create_index(
        'ix_incident_source_source_name_source_record_id',
        'incident_source',
        ['source_name', 'source_record_id'],
        unique=False,
    )


def downgrade():
    op.drop_index('ix_incident_source_source_name_source_record_id', table_name='incident_source')
    op.drop_index(op.f('ix_incident_source_source_record_id'), table_name='incident_source')
    op.drop_column('incident_source', 'confidence_level')
    op.drop_column('incident_source', 'source_record_id')

