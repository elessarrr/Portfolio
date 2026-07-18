"""add pg_trgm GIN index on aircraft.model_name

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-17 23:50:00.000000

Backs the fuzzy (trigram-similarity) search wired into the /search route. The
pg_trgm extension is already enabled (migration 7272cefb04d4); this adds the GIN
index that makes similarity() / ILIKE fuzzy lookups index-backed on Postgres.

Postgres-only: SQLite (dev/tests) has no pg_trgm, so both directions guard on the
dialect and are no-ops on SQLite.
"""
from alembic import op


# revision identifiers, used by Alembic.
revision = 'c3d4e5f6a7b8'
down_revision = 'b2c3d4e5f6a7'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_aircraft_model_name_trgm "
            "ON aircraft USING gin (model_name gin_trgm_ops)"
        )


def downgrade():
    conn = op.get_bind()
    if conn.dialect.name == 'postgresql':
        op.execute("DROP INDEX IF EXISTS ix_aircraft_model_name_trgm")
