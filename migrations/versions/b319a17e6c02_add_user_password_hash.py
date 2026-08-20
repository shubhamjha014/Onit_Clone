"""Add passwords for legacy user records.

Revision ID: b319a17e6c02
Revises: 71b34cb24b39
Create Date: 2026-08-18
"""

from alembic import op
import sqlalchemy as sa


revision = "b319a17e6c02"
down_revision = "71b34cb24b39"
branch_labels = None
depends_on = None


# Werkzeug hash for the documented initial password: demo1234.
DEMO_PASSWORD_HASH = (
    "scrypt:32768:8:1$LRJPvlrTiyWpyZ6F$00e25fcb68a77ad0aaf1f187d7ff855"
    "37144be31c4523d295afd7dbed7b15b673ab36e01c3566ac85ec8f69e6856ce9"
    "bc872892750e9f0696a418e4e259b9d65"
)


def upgrade():
    """Repair databases created before password_hash was added to User."""
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password_hash" not in existing_columns:
        op.add_column("users", sa.Column("password_hash", sa.String(length=255), nullable=True))
        bind.execute(
            sa.text("UPDATE users SET password_hash = :password_hash WHERE password_hash IS NULL"),
            {"password_hash": DEMO_PASSWORD_HASH},
        )
        op.alter_column("users", "password_hash", nullable=False)


def downgrade():
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    if "password_hash" in existing_columns:
        op.drop_column("users", "password_hash")
