"""add_jasc_mapping_table

Revision ID: 0f6d7d9c3f2a
Revises: 8d2a1c4f0b17
Create Date: 2026-03-29 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '0f6d7d9c3f2a'
down_revision = '8d2a1c4f0b17'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'jasc_mapping',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('jasc_code', sa.String(length=32), nullable=False),
        sa.Column('jasc_description', sa.String(length=256), nullable=True),
        sa.Column('system_name', sa.String(length=64), nullable=False),
        sa.Column('confidence', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('jasc_code'),
    )
    op.create_index(op.f('ix_jasc_mapping_created_at'), 'jasc_mapping', ['created_at'], unique=False)
    op.create_index(op.f('ix_jasc_mapping_jasc_code'), 'jasc_mapping', ['jasc_code'], unique=False)
    op.create_index(op.f('ix_jasc_mapping_system_name'), 'jasc_mapping', ['system_name'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_jasc_mapping_system_name'), table_name='jasc_mapping')
    op.drop_index(op.f('ix_jasc_mapping_jasc_code'), table_name='jasc_mapping')
    op.drop_index(op.f('ix_jasc_mapping_created_at'), table_name='jasc_mapping')
    op.drop_table('jasc_mapping')

