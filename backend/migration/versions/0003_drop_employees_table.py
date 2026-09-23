"""Drop the employees table; attendance_logs, leave_requests and paychecks
now reference users.id directly (column names kept as employee_id).

Existing rows in those three tables are deleted: their employee_id values
point at the removed employees table and cannot be mapped onto user ids.

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-24
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Rows keyed to the old employees table are meaningless after the drop.
    op.execute("DELETE FROM leave_requests")
    op.execute("DELETE FROM attendance_logs")
    op.execute("DELETE FROM paychecks")

    # CASCADE also removes the old FK constraints on the dependent tables.
    op.execute("DROP TABLE IF EXISTS employees CASCADE")

    op.create_foreign_key(
        "attendance_logs_employee_id_fkey", "attendance_logs", "users",
        ["employee_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "leave_requests_employee_id_fkey", "leave_requests", "users",
        ["employee_id"], ["id"], ondelete="CASCADE",
    )
    op.create_foreign_key(
        "leave_requests_approved_by_id_fkey", "leave_requests", "users",
        ["approved_by_id"], ["id"],
    )
    op.create_foreign_key(
        "paychecks_employee_id_fkey", "paychecks", "users",
        ["employee_id"], ["id"], ondelete="CASCADE",
    )


def downgrade() -> None:
    raise NotImplementedError(
        "Irreversible: the employees table and its dependent rows were dropped."
    )
