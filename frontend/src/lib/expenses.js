/**
 * Payment state of a finance expense row, read from its stored `status`
 * (`paid` / `unpaid` / `overdue`). The backend derives it from `paid_date`
 * and `due_date` on every create and update, and its daily `expense_status`
 * job turns unpaid bills past their due date into overdue.
 */
export function isOverdue(row) {
  return row.status === 'overdue'
}

export function isPaid(row) {
  return row.status === 'paid'
}
