"""merge incident_source link fields and source_name index heads

Revision ID: f6a7b8c9d0e1
Revises: be4e7bb8751a, c8f1a2b3d4e5
Create Date: 2026-06-14
"""

from alembic import op


revision = "f6a7b8c9d0e1"
down_revision = ("be4e7bb8751a", "c8f1a2b3d4e5")
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
