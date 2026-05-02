"""set incident asn_url nullable

Revision ID: 9bf8514d8bc9
Revises: f4a9c2d1e7b3
Create Date: 2026-04-26 23:19:48.079145

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9bf8514d8bc9'
down_revision = 'f4a9c2d1e7b3'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.alter_column(
            'asn_url',
            existing_type=sa.String(length=256),
            nullable=True,
        )


def downgrade():
    # Downgrade safety: normalize nulls before restoring NOT NULL.
    op.execute("UPDATE incident SET asn_url = '' WHERE asn_url IS NULL")
    with op.batch_alter_table('incident', schema=None) as batch_op:
        batch_op.alter_column(
            'asn_url',
            existing_type=sa.String(length=256),
            nullable=False,
        )
