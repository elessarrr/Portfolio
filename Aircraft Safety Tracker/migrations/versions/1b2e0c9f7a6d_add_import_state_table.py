"""add_import_state_table

Revision ID: 1b2e0c9f7a6d
Revises: e580fbb2beb0
Create Date: 2026-03-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '1b2e0c9f7a6d'
down_revision = 'e580fbb2beb0'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'import_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=64), nullable=False),
        sa.Column('last_attempted_at', sa.DateTime(), nullable=True),
        sa.Column('last_successful_at', sa.DateTime(), nullable=True),
        sa.Column('last_status', sa.String(length=32), nullable=True),
        sa.Column('last_import_log_id', sa.Integer(), nullable=True),
        sa.Column('last_records_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_duplicates_detected', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_duplicates_merged', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_errors_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name'),
    )
    op.create_index(op.f('ix_import_state_last_attempted_at'), 'import_state', ['last_attempted_at'], unique=False)
    op.create_index(op.f('ix_import_state_last_successful_at'), 'import_state', ['last_successful_at'], unique=False)
    op.create_index(op.f('ix_import_state_last_status'), 'import_state', ['last_status'], unique=False)
    op.create_index(op.f('ix_import_state_source_name'), 'import_state', ['source_name'], unique=False)
    op.create_index(op.f('ix_import_state_updated_at'), 'import_state', ['updated_at'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_import_state_updated_at'), table_name='import_state')
    op.drop_index(op.f('ix_import_state_source_name'), table_name='import_state')
    op.drop_index(op.f('ix_import_state_last_status'), table_name='import_state')
    op.drop_index(op.f('ix_import_state_last_successful_at'), table_name='import_state')
    op.drop_index(op.f('ix_import_state_last_attempted_at'), table_name='import_state')
    op.drop_table('import_state')

