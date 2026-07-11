"""Payment categories: category/employee_id/contract_number columns, nullable
invoice_id with SET NULL, and the category/reference consistency CHECK.

Every statement is idempotent, because this revision runs against two kinds of
databases: pre-Alembic ones stamped at 0001 whose payments table still has the
old invoice-only shape (all statements apply), and databases created by 0001
itself where the table is already in its final shape (all statements no-op).

The downgrade is destructive: payments without an invoice cannot exist in the
old shape and are deleted.

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-11

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, Sequence[str], None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Order is load-bearing: add column -> backfill -> SET NOT NULL, CHECK last so
# backfilled rows already satisfy it.
UPGRADE_STATEMENTS = [
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS category VARCHAR(50)",
    # Pre-existing rows are all invoice payments by definition
    "UPDATE payments SET category = 'procurement' WHERE category IS NULL",
    "ALTER TABLE payments ALTER COLUMN category SET NOT NULL",
    "CREATE INDEX IF NOT EXISTS ix_payments_category ON payments (category)",
    "ALTER TABLE payments ALTER COLUMN invoice_id DROP NOT NULL",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS employee_id INTEGER REFERENCES employees(id) ON DELETE SET NULL",
    "ALTER TABLE payments ADD COLUMN IF NOT EXISTS contract_number VARCHAR(100)",
    # Flip the invoice FK CASCADE -> SET NULL (payments are cash records and
    # survive invoice deletion), guarded on the current delete action
    # (confdeltype 'c' = cascade) so databases created by 0001 skip it
    """
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
                 WHERE t.relname = 'payments' AND c.conname = 'payments_invoice_id_fkey'
                   AND c.confdeltype = 'c') THEN
        ALTER TABLE payments DROP CONSTRAINT payments_invoice_id_fkey;
        ALTER TABLE payments ADD CONSTRAINT payments_invoice_id_fkey
          FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL;
      END IF;
    END $$
    """,
    """
    DO $$ BEGIN
      IF NOT EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
                     WHERE t.relname = 'payments' AND c.conname = 'ck_payments_category_refs') THEN
        ALTER TABLE payments ADD CONSTRAINT ck_payments_category_refs CHECK (
          (invoice_id IS NULL OR category = 'procurement') AND
          (employee_id IS NULL OR category = 'salary') AND
          (contract_number IS NULL OR category = 'rent'));
      END IF;
    END $$
    """,
]

DOWNGRADE_STATEMENTS = [
    "ALTER TABLE payments DROP CONSTRAINT IF EXISTS ck_payments_category_refs",
    "ALTER TABLE payments DROP COLUMN IF EXISTS contract_number",
    "ALTER TABLE payments DROP COLUMN IF EXISTS employee_id",
    # The old shape requires an invoice on every payment
    "DELETE FROM payments WHERE invoice_id IS NULL",
    "ALTER TABLE payments ALTER COLUMN invoice_id SET NOT NULL",
    """
    DO $$ BEGIN
      IF EXISTS (SELECT 1 FROM pg_constraint c JOIN pg_class t ON t.oid = c.conrelid
                 WHERE t.relname = 'payments' AND c.conname = 'payments_invoice_id_fkey'
                   AND c.confdeltype = 'n') THEN
        ALTER TABLE payments DROP CONSTRAINT payments_invoice_id_fkey;
        ALTER TABLE payments ADD CONSTRAINT payments_invoice_id_fkey
          FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE;
      END IF;
    END $$
    """,
    "DROP INDEX IF EXISTS ix_payments_category",
    "ALTER TABLE payments DROP COLUMN IF EXISTS category",
]


def upgrade() -> None:
    for stmt in UPGRADE_STATEMENTS:
        op.execute(sa.text(stmt))


def downgrade() -> None:
    for stmt in DOWNGRADE_STATEMENTS:
        op.execute(sa.text(stmt))
