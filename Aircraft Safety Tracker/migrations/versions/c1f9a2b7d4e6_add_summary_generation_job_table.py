"""add_summary_generation_job_table

Revision ID: c1f9a2b7d4e6
Revises: aba86b120c64
Create Date: 2026-04-05 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = 'c1f9a2b7d4e6'
down_revision = 'aba86b120c64'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'summary_generation_job',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('aircraft_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('attempts', sa.Integer(), nullable=False),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['aircraft_id'], ['aircraft.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_summary_generation_job_aircraft_id'), 'summary_generation_job', ['aircraft_id'], unique=False)
    op.create_index(op.f('ix_summary_generation_job_created_at'), 'summary_generation_job', ['created_at'], unique=False)
    op.create_index(op.f('ix_summary_generation_job_status'), 'summary_generation_job', ['status'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_summary_generation_job_status'), table_name='summary_generation_job')
    op.drop_index(op.f('ix_summary_generation_job_created_at'), table_name='summary_generation_job')
    op.drop_index(op.f('ix_summary_generation_job_aircraft_id'), table_name='summary_generation_job')
    op.drop_table('summary_generation_job')
