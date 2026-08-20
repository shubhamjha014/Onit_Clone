"""Remove the obsolete plaintext-era user password column.

Revision ID: e56f8a7c2d14
Revises: d42d6e03f1a7
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "e56f8a7c2d14"
down_revision = "d42d6e03f1a7"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password" in columns:
        op.drop_column("users", "password")


def downgrade():
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password" not in columns:
        op.add_column("users", sa.Column("password", sa.String(length=255), nullable=True))
