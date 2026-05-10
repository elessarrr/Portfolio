"""enable_pg_trgm

Revision ID: 7272cefb04d4
Revises: 76d481f2c04c
Create Date: 2025-12-09 21:09:46.772090

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '7272cefb04d4'
down_revision = '76d481f2c04c'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute('CREATE EXTENSION IF NOT EXISTS pg_trgm')


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute('DROP EXTENSION IF EXISTS pg_trgm')
