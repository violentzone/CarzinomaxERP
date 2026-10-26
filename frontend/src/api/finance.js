/**
 * Finance endpoints: /api/v1/finance
 *
 * The finance ledger is an expense log: each record has a UUID, an
 * `expense_type` of `paycheck | petty_cash | investment | other`, an `amount`,
 * and optional vendor, reference, description, category, document / due / paid
 * dates, a dev `project_id` and the `receipt_path` of the document it was booked from.
 */
import { apiGet, apiPost, apiPut, apiDelete, apiPostForm, apiGetBlob } from '../lib/api'

export const EXPENSE_TYPES = ['paycheck', 'petty_cash', 'investment', 'other']
export const EXPENSE_CATEGORIES = ['cloud', 'software_licenses', 'hardware', 'consulting', 'travel', 'office', 'meals', 'other']

export const financeApi = {
  listExpenses: () => apiGet('/finance/expense_list'),
  getExpense: (id) => apiGet(`/finance/expense/${id}`),
  createExpense: (payload) => apiPost('/finance/expense', payload),
  updateExpense: (id, payload) => apiPut(`/finance/expense/${id}`, payload),
  deleteExpense: (id) => apiDelete(`/finance/expense/${id}`),
  /**
   * Upload a receipt or invoice (PNG, JPEG, WebP or PDF, 10 MB max) and have the AI
   * read it. Resolves to `{receipt_path, draft, note}`; `draft` is null when the
   * document could not be read (`note` says why). Nothing is booked: post the
   * confirmed draft plus `receipt_path` through `createExpense`.
   */
  readReceipt: (file) => {
    const form = new FormData()
    form.append('file', file, file.name)
    return apiPostForm('/finance/receipt', form)
  },
  /** The stored receipt of an expense (JPEG or PDF) as a `Blob`; 404 when the expense has none. */
  fetchReceipt: (id) => apiGetBlob(`/finance/expense/${id}/receipt`),
}
