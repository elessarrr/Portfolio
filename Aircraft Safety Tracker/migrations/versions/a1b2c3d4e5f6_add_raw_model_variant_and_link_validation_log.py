"""
Add raw_model_variant, last_validated_at, and LinkValidationLog table.

Revision ID: a1b2c3d4e5f6
Revises: aba86b120c64
Create Date: 2026-04-25

This migration supports PRD-0016: NTSB Link Reliability and Graceful Display.
Changes:
  1. Adds `raw_model_variant` column to `incident` table for storing the original
     precision string from NTSB before any normalization (FR-1, FR-3).
  2. Adds `last_validated_at` column to `incident_source` table to track when
     link validation last succeeded (FR-23, Section 7 technical consideration).
  3. Creates `link_validation_log` table to audit all re-validation outcomes
     (FR-21, FR-24, Section 9.1 schema).
"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f6'
down_revision = 'aba86b120c64'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.add_column(sa.Column('raw_model_variant', sa.String(length=128), nullable=True, index=True))

    with op.batch_alter_table('incident_source', schema=None) as batch_op:
        batch_op.add_column(sa.Column('last_validated_at', sa.DateTime(), nullable=True))

    op.create_table(
        'link_validation_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('incident_source_id', sa.Integer(), nullable=False),
        sa.Column('validated_at', sa.DateTime(), nullable=False),
        sa.Column('old_source_url', sa.String(length=512), nullable=True),
        sa.Column('old_report_url', sa.String(length=512), nullable=True),
        sa.Column('new_source_url', sa.String(length=512), nullable=True),
        sa.Column('new_report_url', sa.String(length=512), nullable=True),
        sa.Column('result', sa.String(length=32), nullable=False),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('error_detail', sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(['incident_source_id'], ['incident_source.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_link_validation_log_incident_source_id', 'link_validation_log', ['incident_source_id'])
    op.create_index('ix_link_validation_log_validated_at', 'link_validation_log', ['validated_at'])


def downgrade():
    op.drop_index('ix_link_validation_log_validated_at', table_name='link_validation_log')
    op.drop_index('ix_link_validation_log_incident_source_id', table_name='link_validation_log')
    op.drop_table('link_validation_log')

    with op.batch_alter_table('incident_source', schema=None) as batch_op:
        batch_op.drop_column('last_validated_at')

    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.drop_column('raw_model_variant')