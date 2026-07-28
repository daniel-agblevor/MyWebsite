"""track Supabase image paths

Revision ID: a31f6c9d7e42
Revises: 5f7c2a91d4b8
Create Date: 2026-07-28
"""

from alembic import op
import sqlalchemy as sa


revision = "a31f6c9d7e42"
down_revision = "5f7c2a91d4b8"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("site_profiles") as batch_op:
        batch_op.add_column(sa.Column("profile_photo_path", sa.String(length=700), nullable=True))
    with op.batch_alter_table("slideshow_images") as batch_op:
        batch_op.add_column(sa.Column("storage_path", sa.String(length=700), nullable=True))


def downgrade():
    with op.batch_alter_table("slideshow_images") as batch_op:
        batch_op.drop_column("storage_path")
    with op.batch_alter_table("site_profiles") as batch_op:
        batch_op.drop_column("profile_photo_path")
