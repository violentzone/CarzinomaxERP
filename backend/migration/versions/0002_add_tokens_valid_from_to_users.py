"""Add users.tokens_valid_from so logout can revoke previously issued JWTs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-09-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("tokens_valid_from", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "tokens_valid_from")
