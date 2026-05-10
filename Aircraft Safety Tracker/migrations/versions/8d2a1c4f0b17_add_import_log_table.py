"""add_import_log_table

Revision ID: 8d2a1c4f0b17
Revises: 4c2f1a0d8e21, 7272cefb04d4
Create Date: 2026-03-29 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '8d2a1c4f0b17'
down_revision = ('4c2f1a0d8e21', '7272cefb04d4')
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'import_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False, server_default='running'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('finished_at', sa.DateTime(), nullable=True),
        sa.Column('records_processed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duplicates_detected', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('duplicates_merged', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('errors_count', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('log_path', sa.String(length=512), nullable=True),
        sa.Column('details', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_import_log_source_name'), 'import_log', ['source_name'], unique=False)
    op.create_index(op.f('ix_import_log_started_at'), 'import_log', ['started_at'], unique=False)
    op.create_index(op.f('ix_import_log_status'), 'import_log', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_import_log_status'), table_name='import_log')
    op.drop_index(op.f('ix_import_log_started_at'), table_name='import_log')
    op.drop_index(op.f('ix_import_log_source_name'), table_name='import_log')
    op.drop_table('import_log')

