"""Add the original_password compatibility field to users.

Revision ID: f70c9b8d3e25
Revises: e56f8a7c2d14
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "f70c9b8d3e25"
down_revision = "e56f8a7c2d14"
branch_labels = None
depends_on = None


def upgrade():
    """Add the field without altering existing users or their password hashes."""
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "original_password" not in columns:
        op.add_column(
            "users", sa.Column("original_password", sa.String(length=255), nullable=True)
        )


def downgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "original_password" in columns:
        op.drop_column("users", "original_password")
