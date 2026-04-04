"""add_report_url_to_incident_source

Revision ID: 4b7c1d2e9a31
Revises: 1b2e0c9f7a6d
Create Date: 2026-03-30 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


revision = '4b7c1d2e9a31'
down_revision = '1b2e0c9f7a6d'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('incident_source', sa.Column('report_url', sa.String(length=512), nullable=True))


def downgrade():
    op.drop_column('incident_source', 'report_url')

