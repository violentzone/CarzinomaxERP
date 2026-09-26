/**
 * Finance endpoints: /api/v1/finance
 *
 * The finance ledger is a typed expense log: each record has a UUID and an
 * `expense_type` of `paycheck | petty_cash | investment | other`.
 */
import { apiGet, apiPost, apiPut, apiDelete } from '../lib/api'

export const EXPENSE_TYPES = ['paycheck', 'petty_cash', 'investment', 'other']

export const financeApi = {
  listExpenses: () => apiGet('/finance/expense_list'),
  getExpense: (id) => apiGet(`/finance/expense/${id}`),
  createExpense: (payload) => apiPost('/finance/expense', payload),
  updateExpense: (id, payload) => apiPut(`/finance/expense/${id}`, payload),
  deleteExpense: (id) => apiDelete(`/finance/expense/${id}`),
}
