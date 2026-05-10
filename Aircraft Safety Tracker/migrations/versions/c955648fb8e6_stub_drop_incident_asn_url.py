"""stub drop incident asn_url

Revision ID: c955648fb8e6
Revises: 9bf8514d8bc9
Create Date: 2026-04-26 23:38:26.518170

"""
# revision identifiers, used by Alembic.
revision = 'c955648fb8e6'
down_revision = '9bf8514d8bc9'
branch_labels = None
depends_on = None


def upgrade():
    """
    Deferred migration stub for the final ASN cutover.

    Intentionally no-op in this release:
    - Keep `incident.asn_url` available for rollback/verification windows.
    - Execute actual drop in a future release once post-cutover monitoring is complete.
    """
    # Future change (next release):
    # with op.batch_alter_table('incident', schema=None) as batch_op:
    #     batch_op.drop_column('asn_url')
    return None


def downgrade():
    """
    No-op because upgrade performs no schema mutation in this deferred stub.
    """
    return None
