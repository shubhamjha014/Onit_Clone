"""Create the initial administrator account.

Revision ID: d42d6e03f1a7
Revises: b319a17e6c02
Create Date: 2026-08-18
"""

from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "d42d6e03f1a7"
down_revision = "b319a17e6c02"
branch_labels = None
depends_on = None


ADMIN_EMAIL = "admin@onit.local"
ADMIN_PASSWORD_HASH = (
    "scrypt:32768:8:1$306LylNpfNOxpebr$303a114fbc87ea89ef687709be6bc2e0"
    "ccdd2fb76e564166eba6a376867cb552419b0eba61fe1d44c21acfb7e487115"
    "6ef24a64798fbb4f2ce0489c6c19b1510"
)


def upgrade():
    users = sa.table(
        "users",
        sa.column("name", sa.String),
        sa.column("email", sa.String),
        sa.column("password", sa.String),
        sa.column("password_hash", sa.String),
        sa.column("created_at", sa.DateTime),
    )
    bind = op.get_bind()
    existing_columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    exists = bind.execute(
        sa.text("SELECT 1 FROM users WHERE email = :email"), {"email": ADMIN_EMAIL}
    ).first()
    if exists is None:
        admin_user = {
            "name": "admin",
            "email": ADMIN_EMAIL,
            "password_hash": ADMIN_PASSWORD_HASH,
            "created_at": datetime.utcnow(),
        }
        # Older installations still require the obsolete password column.
        if "password" in existing_columns:
            admin_user["password"] = ADMIN_PASSWORD_HASH
        op.bulk_insert(
            users,
            [admin_user],
        )


def downgrade():
    op.execute(sa.text("DELETE FROM users WHERE email = :email").bindparams(email=ADMIN_EMAIL))
