"""add profile contact fields

Revision ID: 5f7c2a91d4b8
Revises: 244fab189cf5
Create Date: 2026-07-27
"""

from alembic import op
import sqlalchemy as sa


revision = "5f7c2a91d4b8"
down_revision = "244fab189cf5"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_profiles") as batch_op:
        batch_op.add_column(sa.Column("phone", sa.String(length=40), nullable=True))
        batch_op.add_column(sa.Column("email", sa.String(length=254), nullable=True))


def downgrade():
    with op.batch_alter_table("site_profiles") as batch_op:
        batch_op.drop_column("email")
        batch_op.drop_column("phone")

