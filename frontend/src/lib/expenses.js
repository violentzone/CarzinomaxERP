import { today } from './format'

/**
 * Payment state of a finance expense row. Unpaid = no `paid_date`; overdue =
 * unpaid and `due_date` before today. ISO date strings compare as dates.
 * `today()` is the browser's local date while the summary mail uses the
 * server's, so a bill can flip to overdue at slightly different moments.
 */
export function isOverdue(row) {
  return !row.paid_date && Boolean(row.due_date) && row.due_date < today()
}
