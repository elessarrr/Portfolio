"""add_unmapped_jasc_table

Revision ID: 2a6d4c0b9e12
Revises: 4b7c1d2e9a31
Create Date: 2026-03-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '2a6d4c0b9e12'
down_revision = '4b7c1d2e9a31'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'unmapped_jasc',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_name', sa.String(length=64), nullable=False),
        sa.Column('jasc_code', sa.String(length=32), nullable=False),
        sa.Column('occurrences', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('first_seen_at', sa.DateTime(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_name', 'jasc_code', name='uq_unmapped_jasc_source_name_jasc_code'),
    )
    op.create_index(op.f('ix_unmapped_jasc_first_seen_at'), 'unmapped_jasc', ['first_seen_at'], unique=False)
    op.create_index(op.f('ix_unmapped_jasc_jasc_code'), 'unmapped_jasc', ['jasc_code'], unique=False)
    op.create_index(op.f('ix_unmapped_jasc_last_seen_at'), 'unmapped_jasc', ['last_seen_at'], unique=False)
    op.create_index(op.f('ix_unmapped_jasc_source_name'), 'unmapped_jasc', ['source_name'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_unmapped_jasc_source_name'), table_name='unmapped_jasc')
    op.drop_index(op.f('ix_unmapped_jasc_last_seen_at'), table_name='unmapped_jasc')
    op.drop_index(op.f('ix_unmapped_jasc_jasc_code'), table_name='unmapped_jasc')
    op.drop_index(op.f('ix_unmapped_jasc_first_seen_at'), table_name='unmapped_jasc')
    op.drop_table('unmapped_jasc')

