"""add_dedupe_decision_table

Revision ID: 6c3d9a1e2f0b
Revises: 2a6d4c0b9e12
Create Date: 2026-03-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '6c3d9a1e2f0b'
down_revision = '2a6d4c0b9e12'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'dedupe_decision',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=64), nullable=False),
        sa.Column('source_record_id', sa.String(length=128), nullable=True),
        sa.Column('incoming_incident_id', sa.Integer(), nullable=True),
        sa.Column('matched_incident_id', sa.Integer(), nullable=True),
        sa.Column('decision', sa.String(length=32), nullable=False),
        sa.Column('rule', sa.String(length=64), nullable=True),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_dedupe_decision_created_at'), 'dedupe_decision', ['created_at'], unique=False)
    op.create_index(op.f('ix_dedupe_decision_decision'), 'dedupe_decision', ['decision'], unique=False)
    op.create_index(op.f('ix_dedupe_decision_incoming_incident_id'), 'dedupe_decision', ['incoming_incident_id'], unique=False)
    op.create_index(op.f('ix_dedupe_decision_matched_incident_id'), 'dedupe_decision', ['matched_incident_id'], unique=False)
    op.create_index(op.f('ix_dedupe_decision_rule'), 'dedupe_decision', ['rule'], unique=False)
    op.create_index(op.f('ix_dedupe_decision_source_name'), 'dedupe_decision', ['source_name'], unique=False)
    op.create_index(op.f('ix_dedupe_decision_source_record_id'), 'dedupe_decision', ['source_record_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_dedupe_decision_source_record_id'), table_name='dedupe_decision')
    op.drop_index(op.f('ix_dedupe_decision_source_name'), table_name='dedupe_decision')
    op.drop_index(op.f('ix_dedupe_decision_rule'), table_name='dedupe_decision')
    op.drop_index(op.f('ix_dedupe_decision_matched_incident_id'), table_name='dedupe_decision')
    op.drop_index(op.f('ix_dedupe_decision_incoming_incident_id'), table_name='dedupe_decision')
    op.drop_index(op.f('ix_dedupe_decision_decision'), table_name='dedupe_decision')
    op.drop_index(op.f('ix_dedupe_decision_created_at'), table_name='dedupe_decision')
    op.drop_table('dedupe_decision')

